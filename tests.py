from http.client import responses
from unittest import TestCase
from unittest.mock import patch

from psycopg.errors import UniqueViolation
from requests import session

from backend.app import app
from countries import compare_two_countries


class GameTests(TestCase):
    def test_compare_two_countries(self):
        result = compare_two_countries("Japan", "Germany")

        self.assertEqual(result["Japan"]["Points"], 2)
        self.assertEqual(result["Germany"]["Points"], 0)


class AuthenticationTests(TestCase):
    @patch("backend.app.create_user", return_value=1)
    def test_successful_registration(self, mock_create_user):
        form_data = {"username": "user",
                     "password": "12345678",
                     "email": "user@mail.com"}
        client = app.test_client()
        response = client.post("/register", data=form_data)
        mock_create_user.assert_called_once_with(
            "user", "12345678", "user@mail.com"
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
        form_data = {"username": "user",
                     "password": "12345678",
                     "email": "user@mail.com"}
        client = app.test_client()
        response = client.post("/register", data=form_data)
        self.assertEqual(response.status_code, 409)

    def test_guest_redirection_on_registration_success(self):
        client = app.test_client()
        response = client.get("/registration_success")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    @patch("backend.app.login_user", return_value=True)
    def test_successful_login_without_countries(self, mock_login_user):
        form_data = {"username": "user", "password": "12345678"}
        client = app.test_client()
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

        form_data = {"username": "user", "password": "12345678"}
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