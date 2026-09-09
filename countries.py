import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MY_SECRET_KEY")

#CORE GAME LOGIC
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


def compare_two_countries(country1, country2):
    countries_api_data = get_country_data(country1, country2)

    stats = {
        countries_api_data[0]["Name"]: {"Points": 0,
                                        "Population": countries_api_data[0]["Population"],
                                        "Area(km)": countries_api_data[0]["Area(km)"]},
        countries_api_data[1]["Name"]: {"Points": 0,
                                        "Population": countries_api_data[1]["Population"],
                                        "Area(km)": countries_api_data[1]["Area(km)"]}
    }

    if countries_api_data[0]["Population"] > countries_api_data[1]["Population"]:
        stats[countries_api_data[0]["Name"]]["Points"] += 1
    elif countries_api_data[1]["Population"] > countries_api_data[0]["Population"]:
        stats[countries_api_data[1]["Name"]]["Points"] += 1
    if countries_api_data[0]["Area(km)"] > countries_api_data[1]["Area(km)"]:
        stats[countries_api_data[0]["Name"]]["Points"] += 1
    elif countries_api_data[1]["Area(km)"] > countries_api_data[0]["Area(km)"]:
        stats[countries_api_data[1]["Name"]]["Points"] += 1
    return stats


if __name__ == "__main__":
    def ask_for_country():
        while True:
            country_name1 = input("Enter 1st country: ")
            country_name2 = input("Enter 2nd country: ")

            try:
                return get_country_data(country_name1, country_name2)
            except ValueError:
                print("Country not found, try again")


    def display_final_score():
        final_scores = compare_two_countries()

        countries = list(final_scores.keys())

        country1 = countries[0]
        country2 = countries[1]

        score1 = final_scores[country1]["Points"]
        score2 = final_scores[country2]["Points"]

        if score1 > score2:
            winner = country1
            loser = country2

        elif score2 > score1:
            winner = country2
            loser = country1

        else:
            return f"\nIt's a DRAW! {country1} and {country2} both have {score1} points."

        winning_stats = final_scores[winner]
        losing_stats = final_scores[loser]

        return (f"\nThe winner is: {winner} with {winning_stats["Points"]} points."
                f"\nPopulation: {winning_stats["Population"]}, Area(km²): {winning_stats["Area(km)"]}"
                f"\n\nThe loser is: {loser} with {losing_stats["Points"]} points."
                f"\nPopulation: {losing_stats["Population"]}, Area(km²): {losing_stats["Area(km)"]}")
