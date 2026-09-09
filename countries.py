import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MY_SECRET_KEY")

def get_one_country(country):
    response = requests.get(
        f"https://api.restcountries.com/countries/v5/names.common/{country.lower()}",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    data = response.json()
    if not data["data"]["objects"]:
        response = requests.get(
            f"https://api.restcountries.com/countries/v5/names.alternates/{country.lower()}",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        data = response.json()
        if not data["data"]["objects"]:
            raise ValueError("This country was not found.")
    country_data = data["data"]["objects"][0]

    return {
        "Name": country_data["names"]["common"],
        "Population": country_data["population"],
        "Area(km)": country_data["area"]["kilometers"]
    }


def get_country_data(country1, country2):
    return get_one_country(country1), get_one_country(country2)


def ask_for_country():
    country_name1 = input("Enter 1st country: ")
    country_name2 = input("Enter 2nd country: ")
    return [country_name1, country_name2]


def compare_two_countries():
    selected_countries = ask_for_country()
    countries_api_data = (get_country_data(selected_countries[0], selected_countries[1]))
    points = {
        countries_api_data[0]["Name"]: 0,
        countries_api_data[1]["Name"]: 0
    }
    if countries_api_data[0]["Population"] > countries_api_data[1]["Population"]:
        points[countries_api_data[0]["Name"]] += 1
    elif countries_api_data[1]["Population"] > countries_api_data[0]["Population"]:
        points[countries_api_data[1]["Name"]] += 1
    if countries_api_data[0]["Area(km)"] > countries_api_data[1]["Area(km)"]:
        points[countries_api_data[0]["Name"]] += 1
    elif countries_api_data[1]["Area(km)"] > countries_api_data[0]["Area(km)"]:
        points[countries_api_data[1]["Name"]] += 1
    return points


def display_final_score():
    final_scores = compare_two_countries()

    countries = list(final_scores.keys())
    scores = list(final_scores.values())

    country1 = countries[0]
    score1 = scores[0]

    country2 = countries[1]
    score2 = scores[1]

    if score1 > score2:
        winner = country1
        winning_score = score1
        losing_score = score2
        loser = country2
    elif score2 > score1:
        winner = country2
        winning_score = score2
        losing_score = score1
        loser = country1
    else:
        return f"\nIt's a DRAW! {country1} and {country2} both have {score1} points."
    return (f"\nThe winner is: {winner}! with {winning_score} points."
            f"\nThe looser is {loser} with {losing_score} points.")

print(display_final_score())