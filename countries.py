import requests

def get_one_country(country):
    response = requests.get(
        f"https://api.restcountries.com/countries/v5?q={country.lower()}",
        headers={"Authorization": "Bearer rc_live_84c8dba8a4d94c4ba277af54202d0c0c"}
    )

    data = response.json()
    country_data = data["data"]["objects"][0]

    return {
        "Name": country_data["names"]["common"],
        "Population": country_data["population"],
        "Area(km)": country_data["area"]["kilometers"]
    }


def get_country_data(country1, country2):
    return get_one_country(country1), get_one_country(country2)

def ask_for_country():
    country_name1 = input("Enter your 1st country: ")
    country_name2 = input("Enter your 2nd country: ")
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

print(compare_two_countries())