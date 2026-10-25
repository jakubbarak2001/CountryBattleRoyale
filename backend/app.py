import re
from secrets import token_urlsafe

import psycopg.errors
from email_validator import validate_email, EmailNotValidError
from flask import Flask, render_template, request, session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
import os
from dotenv import load_dotenv
from werkzeug.utils import redirect

from backend.db import create_user, login_user, read_rounds_played, \
    read_rounds_won, read_best_streak, create_round, complete_round
from countries import compare_two_countries, select_and_compare_random_countries

load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
csrf = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
    strategy="moving-window",
)

def get_game_context(country_comparison=None):
    country_1, country_2 = session["current_countries"]
    if country_comparison is None:
        country_comparison = compare_two_countries(country_1, country_2)

    return {
        "country_1": country_1,
        "country_2": country_2,
        "country_1_flag": country_comparison[country_1]["Flag"],
        "country_2_flag": country_comparison[country_2]["Flag"],
        "streak": session.get("streak", 0),
        "data": None,
    }

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        session.permanent = True
        country_comparison = None

        if ("current_countries" not in session or "round_id" not in session
                or session.get("answered", False)
                or request.args.get("new_matchup") == "1"):
            country_comparison = select_and_compare_random_countries()
            session["current_countries"] = list(country_comparison.keys())
            session["answered"] = False
            if not session.get("guest_id"):
                session["guest_id"] = token_urlsafe(32)

            if session.get("logged") and session.get("user_id"):
                session["round_id"] = create_round(user_id=session["user_id"])
            else:
                session["round_id"] = create_round(guest_id=session["guest_id"])

        template = "_arena.html" if request.headers.get("X-Requested-With") == "fetch" else "index.html"
        return render_template(template, **get_game_context(country_comparison))

    if request.method == "POST":
        if "current_countries" not in session or "round_id" not in session:
            return jsonify(errors={"form": "Load a new matchup before answering."}), 400
        guess = request.form.get("guess")
        if guess not in ("country1", "country2", "draw"):
            return jsonify(errors={"form": "Choose a country or a draw."}), 400
        country_1, country_2 = session["current_countries"]

        country_comparison = compare_two_countries(country_1, country_2)

        is_correct = False
        if guess == "country1":
            if country_comparison[country_1]["Points"] > country_comparison[country_2]["Points"]:
                is_correct = True
        if guess == "country2":
            if country_comparison[country_2]["Points"] > country_comparison[country_1]["Points"]:
                is_correct = True
        if guess == "draw":
            if country_comparison[country_1]["Points"] == country_comparison[country_2]["Points"]:
                is_correct = True

        streak = session.get("streak", 0) + 1 if is_correct else 0
        user_id = session.get("user_id") if session.get("logged") else None
        if not complete_round(
            session["round_id"], user_id=user_id,
            guest_id=session.get("guest_id"), is_correct=is_correct, streak=streak,
        ):
            # The cookie can be old; the database decides whether this counts.
            session["answered"] = True
            return jsonify(errors={"form": "This round is unavailable or already answered. Load a new matchup."}), 409

        session["streak"] = streak
        session["answered"] = True

        game_context = get_game_context(country_comparison)
        game_context.update(data=country_comparison, is_correct=is_correct)
        return render_template("_arena.html", **game_context)

@app.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    username = request.form.get("username", "")
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    try:

        fields = {
            "username": username,
            "email": email,
            "password": password,
        }

        for field, value in fields.items():
            if value == "":
                errors = {field: f"The {field} is empty, enter some value."}
                return jsonify(errors=errors), 400
        if re.fullmatch("[A-Za-z0-9_]{3,30}", username) is None:
            errors = {
                "username": "Username must contain 3-30 letters, digits or underscores."
            }
            return jsonify(errors=errors), 400

        if len(email) > 254:
            errors = {"email": "Your email address is not in valid format."}
            return jsonify(errors=errors), 400
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            errors = {"email": "Your email address is not in valid format."}
            return jsonify(errors=errors), 400

        if not 8 <= len(password) <= 128:
            errors = {"password": "Your password must be between 8 and 128 characters."}
            return jsonify(errors=errors), 400
        with open("10k-most-common.txt", "r") as file:
            for line in file:
                if password == line.strip("\r\n"):
                    errors = {"password": "Your password is too common, try different one."}
                    return jsonify(errors=errors), 400

        session["user_id"] = create_user(username, password, email)
        session["logged"] = True
        session["username"] = username
        return jsonify(success=True, name=username, logged=session["logged"]), 201

    except psycopg.errors.UniqueViolation as exc:
        error = exc.diag.constraint_name

        if error == "users_username_key":
            errors = {"username": "The username is already taken!"}
        elif error == "users_email_key":
            errors = {"email": "The email is already taken!"}
        else:
            errors = {"form": "Something went wrong."}
    return jsonify(errors=errors), 409

@app.route("/registration_success", methods=["GET"])
def registration_success():

    if session.get("logged", False) and session.get("username"):
        return render_template("registration_success.html", name=session["username"])
    else:
        return redirect("/")


@app.route("/login", methods=["POST"])
@limiter.limit("30 per 15 minutes")
def login():

    username = request.form["username"]
    user_id = login_user(request.form["username"], request.form["password"])
    if user_id:
        session["user_id"] = user_id
        session["logged"] = True
        session["username"] = username
        if "current_countries" not in session:
            return redirect("/")

        return render_template("index.html", **get_game_context())

    else:
        errors = "Wrong username/password combination!"
        return jsonify(errors=errors), 401


@app.route("/logout", methods=["POST"])
def logout():

    session["logged"] = False
    session.pop("username", None)
    session.pop("user_id", None)
    session.pop("round_id", None)
    session.pop("current_countries", None)
    session["streak"] = 0
    return redirect("/")


def render_account(section: str = "account", rounds_played=None, rounds_won=None, best_streak=None,
                   rounds_lost=None, precision=None, current_streak=None):

    if session.get("logged", False) and session.get("username"):
        return render_template(
            "account.html",
            name=session["username"],
            section=section,
            rounds_played=rounds_played,
            rounds_won=rounds_won,
            rounds_lost=rounds_lost,
            precision=precision,
            current_streak=current_streak,
            best_streak=best_streak,
        )

    else:
        return redirect("/")

@app.route("/account", methods=["GET"])
def account():
    return render_account()


@app.route("/account/stats", methods=["GET"])
def stats():
    if session.get("logged", False) and session.get("username"):
        rounds = read_rounds_played(session["username"])
        rounds_won = read_rounds_won(session["username"])
        best_streak = read_best_streak(session["username"])
        rounds_lost = None
        precision = None

        if rounds is not None and rounds_won is not None:
            rounds_lost = rounds - rounds_won
            if rounds > 0:
                precision = (rounds_won / rounds) * 100 if rounds > 0 else 0.0

        return render_account(
            "stats",
            rounds_played=rounds,
            rounds_won=rounds_won,
            rounds_lost=rounds_lost,
            precision=precision,
            current_streak=session.get("streak", 0),
            best_streak=best_streak,
        )

    else:
        return redirect("/")


@app.route("/account/achievements", methods=["GET"])
def achievements():
    return render_account("achievements")


@app.route("/account/settings", methods=["GET"])
def settings():
    return render_account("settings")


if __name__ == "__main__":
    app.run()
