from flask import Flask, render_template, request

from countries import compare_two_countries, select_and_compare_random_countries

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        random_countries = select_and_compare_random_countries()
        country_names = list(random_countries.keys())

        country_1 = country_names[0]
        country_2 = country_names[1]

        return render_template(
            "index.html",
            data=None,
            country_1=country_1,
            country_2=country_2
        )

    if request.method == "POST":
        country_1 = request.form["country1"]
        country_2 = request.form["country2"]
        guess = request.form["guess"]

        battle_data = compare_two_countries(country_1, country_2)

        print(country_1)
        print(country_2)
        print(guess)

        return render_template(
            "index.html",
            data=battle_data,
            country_1=country_1,
            country_2=country_2
        )


if __name__ == "__main__":
    app.run(debug=True)