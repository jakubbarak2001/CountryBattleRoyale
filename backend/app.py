import psycopg.errors
from argon2.exceptions import VerifyMismatchError
from flask import Flask, render_template, request, session, jsonify, url_for
import os
from dotenv import load_dotenv
from werkzeug.utils import redirect

from backend.db import create_user, login_user
from countries import compare_two_countries, select_and_compare_random_countries

load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]


def get_game_context():
    country_1, country_2 = session["current_countries"]
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

        if session.get("logged", False):
            print("Logged")

        if "current_countries" not in session or session.get("answered", False):
            country_comparison = select_and_compare_random_countries()
            session["current_countries"] = list(country_comparison.keys())
            session["answered"] = False

        return render_template(
            "index.html",
            **get_game_context(),
        )

    if request.method == "POST":
        country_1 = request.form["country1"]
        country_2 = request.form["country2"]
        guess = request.form["guess"]

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


        if is_correct and not session["answered"]:
            session["streak"] = session.get("streak", 0) + 1
        elif not is_correct and not session["answered"]:
            session["streak"] = 0
        elif session["answered"]:
            print("You have already answered!")

        session["answered"] = True

        return render_template(
            "index.html",
            data=country_comparison,
            is_correct=is_correct,
            streak=session.get("streak", 0),
            country_1=country_1,
            country_2=country_2,
            country_1_flag=country_comparison[country_1]["Flag"],
            country_2_flag=country_comparison[country_2]["Flag"]
        )

@app.route("/register", methods=["POST"])
def register():

    name = request.form["username"]
    try:
        create_user(request.form["username"], request.form["password"], request.form["email"])
        session["logged"] = True
        session["username"] = name
        return jsonify(success=True, name=name, logged=session["logged"]), 201

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
def login():

    username = request.form["username"]
    valid_login =  login_user(request.form["username"], request.form["password"])
    if valid_login:
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
    if "current_countries" not in session:
        return redirect("/")

    return render_template("index.html", **get_game_context())


def render_account(section: str = "account"):

    if session.get("logged", False) and session.get("username"):
        return render_template("account.html",
                               name = session["username"], section = section)

    else:
        return redirect("/")

@app.route("/account", methods=["GET"])
def account():
    return render_account()


@app.route("/account/stats", methods=["GET"])
def stats():
    return render_account("stats")


@app.route("/account/achievements", methods=["GET"])
def achievements():
    return render_account("achievements")


@app.route("/account/settings", methods=["GET"])
def settings():
    return render_account("settings")


if __name__ == "__main__":
    app.run(debug=True)
