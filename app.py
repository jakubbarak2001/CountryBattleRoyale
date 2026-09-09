from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        result = request.form
        country_1 = result["country1"]
        country_2 = result["country2"]
        print(country_1)
        print(country_2)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)