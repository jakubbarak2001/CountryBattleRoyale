import json
import time
from functools import lru_cache
from pathlib import Path
from random import sample
from tempfile import NamedTemporaryFile

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MY_SECRET_KEY")


@lru_cache(maxsize=1)
def _read_country_cache(path, modified_ns, size, inode):
    """Reuse one indexed snapshot until the file changes, in each worker."""
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["timestamp"], {
        country["names"]["common"].casefold(): country
        for country in data["countries"]
    }


def _cached_countries():
    path = Path("countries.json").resolve()
    stat = path.stat()
    return _read_country_cache(str(path), stat.st_mtime_ns, stat.st_size, stat.st_ino)


def _country_catalog():
    try:
        timestamp, countries = _cached_countries()
    except FileNotFoundError:
        refresh_country_cache()
        timestamp, countries = _cached_countries()

    if time.time() - timestamp > 604800:
        refresh_country_cache()
        _, countries = _cached_countries()
    return countries


def _country_details(country, catalog):
    try:
        data = catalog[country.casefold()]
    except KeyError:
        raise ValueError("This country was not found.") from None
    return {
        "Name": data["names"]["common"],
        "Population": data["population"],
        "Area(km)": data["area"]["kilometers"],
        "Flag": data["flag"]["emoji"],
    }


#CORE GAME LOGIC
def get_one_country(country):
    return _country_details(country, _country_catalog())


def get_country_data(country1, country2):
    catalog = _country_catalog()
    return _country_details(country1, catalog), _country_details(country2, catalog)


def compare_two_countries(country1, country2):
    country_details = get_country_data(country1, country2)

    stats = {
        country_details[0]["Name"]: {"Points": 0,
                                        "Population": country_details[0]["Population"],
                                        "Area(km)": country_details[0]["Area(km)"],
                                        "Flag": country_details[0]["Flag"]},
        country_details[1]["Name"]: {"Points": 0,
                                        "Population": country_details[1]["Population"],
                                        "Area(km)": country_details[1]["Area(km)"],
                                        "Flag": country_details[1]["Flag"]}
    }

    if country_details[0]["Population"] > country_details[1]["Population"]:
        stats[country_details[0]["Name"]]["Points"] += 1
    elif country_details[1]["Population"] > country_details[0]["Population"]:
        stats[country_details[1]["Name"]]["Points"] += 1
    if country_details[0]["Area(km)"] > country_details[1]["Area(km)"]:
        stats[country_details[0]["Name"]]["Points"] += 1
    elif country_details[1]["Area(km)"] > country_details[0]["Area(km)"]:
        stats[country_details[1]["Name"]]["Points"] += 1
    return stats


def select_and_compare_random_countries():
    country_names = list(_country_catalog())
    country1, country2 = sample(country_names, 2)

    return compare_two_countries(country1, country2)

def refresh_country_cache():
    response1 = requests.get(
        "https://api.restcountries.com/countries/v5?limit=100",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10
    )
    response1.raise_for_status()

    response2 = requests.get(
        "https://api.restcountries.com/countries/v5?limit=100&offset=100",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10
    )
    response2.raise_for_status()

    response3 = requests.get(
        "https://api.restcountries.com/countries/v5?limit=100&offset=200",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10
    )
    response3.raise_for_status()

    timestamp = time.time()
    countries = response1.json()["data"]["objects"] + response2.json()["data"]["objects"] + response3.json()["data"]["objects"]
    countries_timestamp = {"timestamp": timestamp, "countries": countries}

    # Other workers must see either complete snapshot, never a partial write.
    path = Path("countries.json").resolve()
    temporary_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                prefix=".countries-", suffix=".json", delete=False) as file:
            temporary_path = Path(file.name)
            json.dump(countries_timestamp, file, indent=2)
        os.replace(temporary_path, path)
        _read_country_cache.cache_clear()
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def is_country_cache_expired():
    timestamp, _ = _cached_countries()
    return time.time() - timestamp > 604800

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
