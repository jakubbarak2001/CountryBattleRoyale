from flask import Flask, render_template, request

from countries import compare_two_countries

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        result = request.form
        country_1 = result["country1"]
        country_2 = result["country2"]
        try:
            battle_data = compare_two_countries(country_1, country_2)
        except ValueError:
            battle_data = "One of those countries doesn't exist, try again."
    else:
        battle_data = "Enter the country names!"
    return render_template('index.html', data=battle_data)

if __name__ == '__main__':
    app.run(debug=True)