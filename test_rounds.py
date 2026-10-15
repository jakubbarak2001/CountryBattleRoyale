"""Replay tests with real PostgreSQL, isolated from the application's tables.

Set TEST_DATABASE_URL to enable. Each test uses its own disposable schema.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from flask import session
from flask_wtf.csrf import generate_csrf

from backend.app import app, limiter
from backend.db import complete_round, create_round


@skipUnless(os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL for PostgreSQL replay tests")
class RoundProtectionTests(TestCase):
    def setUp(self):
        self.enterContext(patch.object(limiter, "_key_prefix", "round-tests-" + uuid4().hex))
        self.dsn = os.environ["TEST_DATABASE_URL"]
        self.schema = "test_rounds_" + uuid4().hex
        self.addCleanup(self.drop_schema)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.test_dsn = make_conninfo(self.dsn, options=f"-csearch_path={self.schema}")
        self.enterContext(patch.dict(os.environ, DATABASE_URL=self.test_dsn))
        with psycopg.connect(self.test_dsn) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, rounds_played INTEGER DEFAULT 0, rounds_won INTEGER DEFAULT 0, best_streak INTEGER DEFAULT 0)")
            conn.execute("INSERT INTO users (id) VALUES (1), (2)")
            # Use the same setup SQL supplied for the Pi installation.
            from pathlib import Path
            conn.execute(Path("docs/sql/rounds.sql").read_text())
        self.countries = {
            "Japan": {"Flag": "JP", "Points": 2, "Population": 100, "Area(km)": 100},
            "Germany": {"Flag": "DE", "Points": 0, "Population": 50, "Area(km)": 50},
        }
        self.enterContext(patch("backend.app.compare_two_countries", return_value=self.countries))
        self.enterContext(patch("backend.app.select_and_compare_random_countries", return_value=self.countries))

    def drop_schema(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))

    def stats(self, user_id=1):
        with psycopg.connect(self.test_dsn) as conn:
            return conn.execute("SELECT rounds_played, rounds_won, best_streak FROM users WHERE id = %s", (user_id,)).fetchone()

    def browser(self, logged=True):
        client = app.test_client()
        with client.session_transaction() as saved:
            if logged:
                saved.update(logged=True, user_id=1, username="user")
        self.assertEqual(client.get("/").status_code, 200)
        with app.test_request_context():
            token = generate_csrf()
            with client.session_transaction() as saved:
                saved["csrf_token"] = session["csrf_token"]
        return client, token

    def test_old_cookie_replay_cannot_award_again(self):
        client, token = self.browser()
        cookie = client.get_cookie("session").value
        data = {"guess": "country1", "csrf_token": token}
        self.assertEqual(client.post("/", data=data).status_code, 200)
        self.assertEqual(self.stats(), (1, 1, 1))
        self.assertEqual(client.post("/", data=data).status_code, 409)
        client.set_cookie("session", cookie)
        self.assertEqual(client.post("/", data=data).status_code, 409)
        self.assertEqual(self.stats(), (1, 1, 1))

    def test_guest_cookie_replay_cannot_count_again(self):
        client, token = self.browser(logged=False)
        cookie = client.get_cookie("session").value
        data = {"guess": "country1", "csrf_token": token}
        self.assertEqual(client.post("/", data=data).status_code, 200)
        client.set_cookie("session", cookie)
        self.assertEqual(client.post("/", data=data).status_code, 409)
        self.assertEqual(self.stats(), (0, 0, 0))

    def test_submitted_countries_cannot_replace_matchup(self):
        client, token = self.browser()
        response = client.post("/", data={"guess": "draw", "country1": "Japan", "country2": "Japan", "csrf_token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stats(), (1, 0, 0))

    def test_invalid_guess_and_missing_round_do_not_count(self):
        client, token = self.browser()
        self.assertEqual(client.post("/", data={"guess": "anything", "csrf_token": token}).status_code, 400)
        with client.session_transaction() as saved:
            del saved["round_id"]
        self.assertEqual(client.post("/", data={"guess": "country1", "csrf_token": token}).status_code, 400)
        self.assertEqual(self.stats(), (0, 0, 0))

    def test_new_matchup_is_one_row_with_correct_owner(self):
        for logged in (True, False):
            with self.subTest(logged=logged):
                client, _ = self.browser(logged)
                with client.session_transaction() as saved:
                    round_id = saved["round_id"]
                    guest_id = saved["guest_id"]
                self.assertEqual(client.get("/").status_code, 200)
                with psycopg.connect(self.test_dsn) as conn:
                    row = conn.execute("SELECT user_id, guest_id, completed FROM rounds WHERE round_id = %s", (round_id,)).fetchone()
                self.assertEqual(row, (1, None, False) if logged else (None, guest_id, False))
        with psycopg.connect(self.test_dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM rounds").fetchone()[0], 2)

    def test_concurrent_submissions_award_exactly_once(self):
        round_id = create_round(user_id=1)
        def submit(_):
            return complete_round(round_id, user_id=1, is_correct=True, streak=1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(submit, range(8)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(self.stats(), (1, 1, 1))

    def test_wrong_owner_cannot_complete_round(self):
        round_id = create_round(user_id=1)
        self.assertFalse(complete_round(round_id, user_id=2))
        guest_round = create_round(guest_id="owner")
        self.assertFalse(complete_round(guest_round, guest_id="stranger"))
        self.assertTrue(complete_round(guest_round, guest_id="owner"))
        self.assertTrue(complete_round(round_id, user_id=1))
        self.assertEqual(self.stats(2), (0, 0, 0))

    def test_failed_statistics_write_rolls_back_round_completion(self):
        round_id = create_round(user_id=1)
        with psycopg.connect(self.test_dsn) as conn:
            conn.execute("ALTER TABLE users ADD CONSTRAINT fail_score CHECK (rounds_played = 0)")
        with self.assertRaises(psycopg.errors.CheckViolation):
            complete_round(round_id, user_id=1, is_correct=True, streak=1)
        with psycopg.connect(self.test_dsn) as conn:
            self.assertFalse(conn.execute("SELECT completed FROM rounds WHERE round_id = %s", (round_id,)).fetchone()[0])
            conn.execute("ALTER TABLE users DROP CONSTRAINT fail_score")
        self.assertTrue(complete_round(round_id, user_id=1, is_correct=True, streak=1))
        self.assertEqual(self.stats(), (1, 1, 1))

    def test_guest_round_can_finish_after_login(self):
        client, token = self.browser(logged=False)
        with patch("backend.app.login_user", return_value=1):
            self.assertEqual(client.post("/login", data={"username": "user", "password": "test", "csrf_token": token}).status_code, 200)
        data = {"guess": "country1", "csrf_token": token}
        self.assertEqual(client.post("/", data=data).status_code, 200)
        self.assertEqual(self.stats(), (1, 1, 1))
        self.assertEqual(client.post("/", data=data).status_code, 409)

    def test_logout_discards_account_round(self):
        client, token = self.browser()
        self.assertEqual(client.post("/logout", data={"csrf_token": token}).status_code, 302)
        with client.session_transaction() as saved:
            self.assertNotIn("user_id", saved)
            self.assertNotIn("round_id", saved)
        self.assertEqual(client.get("/").status_code, 200)
        with client.session_transaction() as saved:
            round_id = saved["round_id"]
        with psycopg.connect(self.test_dsn) as conn:
            self.assertIsNone(conn.execute("SELECT user_id FROM rounds WHERE round_id = %s", (round_id,)).fetchone()[0])
