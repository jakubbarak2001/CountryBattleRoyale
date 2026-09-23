import psycopg.errors
from flask import Flask, render_template, request, session, jsonify
import os
from dotenv import load_dotenv

from backend.db import create_user
from countries import compare_two_countries, select_and_compare_random_countries

load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]


def get_game_context():
    country_1, country_2 = session["current_countries"]
    random_countries = compare_two_countries(country_1, country_2)

    return {
        "country_1": country_1,
        "country_2": country_2,
        "country_1_flag": random_countries[country_1]["Flag"],
        "country_2_flag": random_countries[country_2]["Flag"],
        "streak": session.get("streak", 0),
        "data": None,
    }

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":

        if session.get("logged", False):
            print("Logged")

        if "current_countries" not in session or session.get("answered", False):
            random_countries = select_and_compare_random_countries()
            session["current_countries"] = list(random_countries.keys())
            session["answered"] = False

        return render_template(
            "index.html",
            **get_game_context(),
        )

    if request.method == "POST":
        country_1 = request.form["country1"]
        country_2 = request.form["country2"]
        guess = request.form["guess"]

        battle_data = compare_two_countries(country_1, country_2)

        is_correct = False
        if guess == "country1":
            if battle_data[country_1]["Points"] > battle_data[country_2]["Points"]:
                is_correct = True
        if guess == "country2":
            if battle_data[country_2]["Points"] > battle_data[country_1]["Points"]:
                is_correct = True
        if guess == "draw":
            if battle_data[country_1]["Points"] == battle_data[country_2]["Points"]:
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
            data=battle_data,
            is_correct=is_correct,
            streak=session.get("streak", 0),
            country_1=country_1,
            country_2=country_2,
            country_1_flag=battle_data[country_1]["Flag"],
            country_2_flag=battle_data[country_2]["Flag"]
        )

@app.route("/register", methods=["POST"])
def register():

    if request.method == "POST":
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

    return render_template("registration_success.html", name=session["username"])

#TODO: Feat(backend) timestamp and db connection for last login
#TODO: Feat(db) new last_login columns in existing DB
#TODO: Add Guest opening / without missing-session-key-error TEST
#TODO: Add Attempted registration using existing username / email causes UniqueViolation TEST

@app.route("/login", methods=["POST"])
def login():
    pass


if __name__ == "__main__":
    app.run(debug=True)
