from http.client import responses
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from flask import session
from flask_wtf.csrf import generate_csrf
from psycopg.errors import UniqueViolation

import backend.app
from backend.app import app, limiter
from countries import compare_two_countries


class GameTests(TestCase):
    @patch("countries.get_country_data")
    def test_compare_two_countries(self, mock_country_data):
        mock_country_data.return_value = (
            {"Name": "Japan", "Population": 125_000_000,
             "Area(km)": 377_975, "Flag": "JP"},
            {"Name": "Germany", "Population": 83_000_000,
             "Area(km)": 357_022, "Flag": "DE"},
        )
        result = compare_two_countries("Japan", "Germany")

        self.assertEqual(result["Japan"]["Points"], 2)
        self.assertEqual(result["Germany"]["Points"], 0)


class AuthenticationTests(TestCase):
    def setUp(self):
        # Keep real Redis checks, but isolate each test from other attempts.
        self.enterContext(
            patch.object(limiter, "_key_prefix", f"unittest-{uuid4().hex}")
        )
        self.mock_read_rounds_won = self.enterContext(
            patch("backend.app.read_rounds_won", return_value=0, create=True)
        )
        self.mock_read_best_streak = self.enterContext(
            patch("backend.app.read_best_streak", return_value=0)
        )
        self.mock_write_best_streak = self.enterContext(
            patch("backend.app.write_best_streak")
        )

    def csrf_token(self, client):
        # Give the test browser a token and its matching session value.
        with app.test_request_context():
            token = generate_csrf()
            with client.session_transaction() as saved_session:
                saved_session["csrf_token"] = session["csrf_token"]
        return token

    @patch("backend.app.create_user", return_value=1)
    def test_successful_registration(self, mock_create_user):
        client = app.test_client()
        form_data = {"username": "user",
                     "password": "Raven!27",
                     "email": "user@mail.com",
                     "csrf_token": self.csrf_token(client)}
        response = client.post("/register", data=form_data)
        mock_create_user.assert_called_once_with(
            "user", "Raven!27", "user@mail.com"
          )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertIs(body["success"], True)
        self.assertEqual(body["name"], "user")
        self.assertIs(body["logged"], True)
        with client.session_transaction() as saved_session:
            self.assertIs(saved_session["logged"], True)
            self.assertEqual(saved_session["username"], "user")
        page = client.get("/registration_success")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Hello, user", page.get_data(as_text=True))

    @patch("backend.app.select_and_compare_random_countries")
    @patch("backend.app.compare_two_countries")
    def test_guest_user(self, mock_compare, mock_select):
        fake_countries = {
            "Japan": {"Flag": "JP"},
            "Germany": {"Flag": "DE"},
        }
        mock_select.return_value = fake_countries
        mock_compare.return_value = fake_countries
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Register", response.get_data(as_text=True))

    @patch("backend.app.create_user", side_effect=UniqueViolation)
    def test_existing_credentials_cause_unique_violation(self, mock_create_user):
        client = app.test_client()
        form_data = {"username": "user",
                     "password": "Raven!27",
                     "email": "user@mail.com",
                     "csrf_token": self.csrf_token(client)}
        response = client.post("/register", data=form_data)
        self.assertEqual(response.status_code, 409)
        mock_create_user.assert_called_once_with(
            "user", "Raven!27", "user@mail.com"
        )

    def assert_registration_rejected(self, field, value, *, missing=False):
        form_data = {
            "username": "user",
            "email": "user@mail.com",
            "password": "Raven!27",
        }
        if missing:
            del form_data[field]
        else:
            form_data[field] = value
        client = app.test_client()
        form_data["csrf_token"] = self.csrf_token(client)

        with patch("backend.app.create_user") as mock_create_user:
            response = client.post("/register", data=form_data)

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertEqual(set(body["errors"]), {field})
        self.assertTrue(body["errors"][field])
        mock_create_user.assert_not_called()
        with client.session_transaction() as saved_session:
            self.assertFalse(saved_session.get("logged", False))
            self.assertNotIn("username", saved_session)

    def test_registration_rejects_missing_fields(self):
        for field in ("username", "email", "password"):
            with self.subTest(field=field):
                self.assert_registration_rejected(field, None, missing=True)

    def test_registration_rejects_empty_fields(self):
        for field in ("username", "email", "password"):
            with self.subTest(field=field):
                self.assert_registration_rejected(field, "")

    def test_registration_rejects_invalid_usernames(self):
        for username in ("ab", "a" * 31, "   ", "john smith", "bob!",
                         "žan", "user\n"):
            with self.subTest(username=username):
                self.assert_registration_rejected("username", username)

    def test_registration_rejects_invalid_email_format(self):
        for email in ("hello", "bob@", "@gmail.com", "a@@b.com", "   "):
            with self.subTest(email=email):
                self.assert_registration_rejected("email", email)

    def test_registration_rejects_excessively_long_email(self):
        # Valid component lengths, but 255 characters in total.
        email = "a" * 64 + "@" + ".".join(["b" * 63, "c" * 63, "d" * 62])
        self.assertEqual(len(email), 255)
        self.assert_registration_rejected("email", email)

    def test_registration_rejects_invalid_password_length(self):
        for password in ("Ab!7xyz", "a" * 129):
            with self.subTest(length=len(password)):
                self.assert_registration_rejected("password", password)

    def test_registration_rejects_common_passwords(self):
        for password in ("12345678", "password", "football"):
            with self.subTest(password=password):
                self.assert_registration_rejected("password", password)

    @patch("backend.app.create_user", return_value=1)
    def test_registration_accepts_valid_boundaries(self, mock_create_user):
        email_at_limit = "a" * 64 + "@" + ".".join(
            ["b" * 63, "c" * 63, "d" * 61]
        )
        self.assertEqual(len(email_at_limit), 254)
        cases = (
            ("Ab_", "user@mail.com", "Raven!27"),
            ("a" * 30, "user@mail.com", "Raven!27" * 16),
            ("Player_42", email_at_limit, "Raven!27"),
            ("Player_42", "user@mail.com", " Raven!27 "),
            ("Player_42", "user@mail.com", "Ráven!27"),
        )
        for username, email, password in cases:
            with self.subTest(username=username, email_length=len(email),
                              password_length=len(password)):
                mock_create_user.reset_mock()
                client = app.test_client()
                response = client.post("/register", data={
                    "username": username,
                    "email": email,
                    "password": password,
                    "csrf_token": self.csrf_token(client),
                })
                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.get_json()["success"])
                mock_create_user.assert_called_once_with(username, password, email)
                with client.session_transaction() as saved_session:
                    self.assertTrue(saved_session["logged"])
                    self.assertEqual(saved_session["username"], username)

    def test_guest_redirection_on_registration_success(self):
        client = app.test_client()
        response = client.get("/registration_success")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    @patch("backend.app.login_user", return_value=True)
    @patch("backend.app.compare_two_countries")
    @patch("backend.app.select_and_compare_random_countries")
    def test_successful_login_without_countries(self, mock_select, mock_compare,
                                               mock_login_user):
        fake_countries = {
            "Japan": {"Flag": "JP"},
            "Germany": {"Flag": "DE"},
        }
        mock_select.return_value = fake_countries
        mock_compare.return_value = fake_countries
        client = app.test_client()
        form_data = {"username": "user", "password": "12345678",
                     "csrf_token": self.csrf_token(client)}
        with client.session_transaction() as saved_session:
            self.assertNotIn("current_countries", saved_session)

        response = client.post("/login", data = form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

        client.get(response.headers["Location"])
        with client.session_transaction() as saved_session:
            self.assertIn("current_countries", saved_session)

    @patch("backend.app.login_user", return_value=True)
    @patch("backend.app.compare_two_countries")
    def test_successful_login_with_countries(self, mock_compare, mock_login_user):
        fake_countries = {
            "Japan": {"Flag": "JP"},
            "Germany": {"Flag": "DE"},
        }
        mock_compare.return_value = fake_countries
        client = app.test_client()
        with client.session_transaction() as saved_session:
            saved_session["current_countries"] = ["Japan", "Germany"]

        form_data = {"username": "user", "password": "12345678",
                     "csrf_token": self.csrf_token(client)}
        response = client.post("/login", data = form_data)
        self.assertEqual(response.status_code, 200)

        with client.session_transaction() as saved_session:
            self.assertEqual(saved_session["current_countries"], ["Japan", "Germany"])

    def test_guest_requests_account(self):
        client = app.test_client()
        response = client.get("/account")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_logged_client_requests_account(self):
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"

        response = client.get("/account")

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.get_data(as_text=True))

    def test_guest_account_stats(self):
        client = app.test_client()
        response = client.get("/account/stats")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_guest_account_achievements(self):
        client = app.test_client()
        response = client.get("/account/achievements")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_guest_account_settings(self):
        client = app.test_client()
        response = client.get("/account/settings")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    @patch("backend.app.read_rounds_played", return_value=0)
    def test_logged_account_stats(self, mock_read_rounds_played):
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"

        response = client.get("/account/stats")

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.get_data(as_text=True))
        self.assertIn("Your stats", response.get_data(as_text=True))

    @patch("backend.app.read_rounds_played", return_value=12)
    def test_logged_account_stats_displays_progress(self, mock_read_rounds_played):
        self.mock_read_rounds_won.return_value = 1234
        self.mock_read_best_streak.return_value = 7
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"

        response = client.get("/account/stats")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertRegex(html, r"<dt>Rounds won</dt>\s*<dd>1,234</dd>")
        self.assertRegex(html, r"<dt>Rounds played</dt>\s*<dd>12</dd>")
        self.assertRegex(html, r"<dt>Best streak</dt>\s*<dd>7</dd>")
        self.mock_read_rounds_won.assert_called_once_with("user")
        self.mock_read_best_streak.assert_called_once_with("user")

    @patch("backend.app.write_rounds_won", create=True)
    @patch("backend.app.read_rounds_played", side_effect=[0, 1])
    @patch("backend.app.compare_two_countries")
    @patch("backend.app.write_rounds_played")
    def test_logged_account_stats_rounds_increment(self, mock_increment, mock_compare, mock_read, mock_won):
        fake_countries = {
            "Japan": {"Flag": "JP", "Points": 2, "Population": 100, "Area(km)": 100},
            "Germany": {"Flag": "DE", "Points": 0, "Population": 50, "Area(km)": 50},
        }
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"
            saved_session["current_countries"] = ["Japan", "Germany"]
            saved_session["answered"] = False

        response = client.get("/account/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("0", response.get_data(as_text=True))
        self.assertIn("Your stats", response.get_data(as_text=True))

        mock_compare.return_value = fake_countries

        response = client.post("/", data={
            "country1": "Japan",
            "country2": "Germany",
            "guess": "country1",
            "csrf_token": self.csrf_token(client),
        })
        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as saved_session:
            self.assertTrue(saved_session["answered"])

        mock_increment.assert_called_once_with("user")
        response = client.get("/account/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("1", response.get_data(as_text=True))
        self.assertIn("Your stats", response.get_data(as_text=True))

    @patch("backend.app.read_rounds_played", side_effect=[0, 1])
    @patch("backend.app.compare_two_countries")
    @patch("backend.app.write_rounds_played")
    def test_logged_account_stats_rounds_won_wrong_answer(self, mock_increment,
                                                          mock_compare,
                                                          mock_read):
        fake_countries = {
            "Japan": {"Flag": "JP", "Points": 2, "Population": 100, "Area(km)": 100},
            "Germany": {"Flag": "DE", "Points": 0, "Population": 50, "Area(km)": 50},
        }
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"
            saved_session["current_countries"] = ["Japan", "Germany"]
            saved_session["answered"] = False

        response = client.get("/account/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("0", response.get_data(as_text=True))
        self.assertIn("Your stats", response.get_data(as_text=True))

        mock_compare.return_value = fake_countries

        with patch("backend.app.write_rounds_won", create=True) as mock_won:
            response = client.post("/", data={
                "country1": "Japan",
                "country2": "Germany",
                "guess": "country2",
                "csrf_token": self.csrf_token(client),
            })

            self.assertEqual(response.status_code, 200)

            with client.session_transaction() as saved_session:
                self.assertTrue(saved_session["answered"])

            mock_increment.assert_called_once_with("user")
            mock_won.assert_not_called()

    @patch("backend.app.read_rounds_played", side_effect=[0, 1])
    @patch("backend.app.compare_two_countries")
    @patch("backend.app.write_rounds_played")
    @patch("backend.app.read_best_streak", return_value=0, create=True)
    @patch("backend.app.write_best_streak", create=True)
    def test_logged_account_stats_rounds_won_correct_answer(
            self, mock_increment_streak, mock_read_streak,
            mock_increment, mock_compare, mock_read
    ):

        fake_countries = {
            "Japan": {"Flag": "JP", "Points": 2, "Population": 100, "Area(km)": 100},
            "Germany": {"Flag": "DE", "Points": 0, "Population": 50, "Area(km)": 50},
        }
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"
            saved_session["current_countries"] = ["Japan", "Germany"]
            saved_session["answered"] = False
            saved_session["streak"] = 0

        response = client.get("/account/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("0", response.get_data(as_text=True))
        self.assertIn("Your stats", response.get_data(as_text=True))
        mock_read_streak.assert_called_once_with("user")

        mock_compare.return_value = fake_countries

        with patch("backend.app.write_rounds_won", create=True) as mock_won:
            response = client.post("/", data={
                "country1": "Japan",
                "country2": "Germany",
                "guess": "country1",
                "csrf_token": self.csrf_token(client),
            })

            self.assertEqual(response.status_code, 200)
            mock_won.assert_called_once_with("user")
            mock_increment_streak.assert_called_once_with("user")

            with client.session_transaction() as saved_session:
                self.assertTrue(saved_session["answered"])
                self.assertEqual(saved_session["streak"], 1)

            mock_increment.assert_called_once_with("user")

    def test_logged_account_achievements(self):
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"

        response = client.get("/account/achievements")

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.get_data(as_text=True))
        self.assertIn("Your achievements", response.get_data(as_text=True))

    def test_logged_account_settings(self):
        client = app.test_client()

        with client.session_transaction() as saved_session:
            saved_session["logged"] = True
            saved_session["username"] = "user"

        response = client.get("/account/settings")

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.get_data(as_text=True))
        self.assertIn("Your settings", response.get_data(as_text=True))
