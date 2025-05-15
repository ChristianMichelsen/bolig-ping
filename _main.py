# %%

import json

import requests
from rich import print

from bolig_ping.data_models import Home, SearchQuery
from bolig_ping.rejseplanen import Journey, Location, TripRequest

# %%


query = SearchQuery(
    address_type=[
        "villa",
        "rækkehus",
        "villalejlighed",
    ],
    # min_price=7_500_000,
    min_price=10_500_000,
    max_price=10_700_000,
    min_size=110,
    max_size=250,
    min_rooms=3,
    max_rooms=8,
    municipality=[
        "lyngby-taarbaek",  # Lyngby / Virum
        "rudersdal",  # Holte",
        "gladsaxe",  # Bagsværd,
        "furesoe",  # Farum
        "gentofte",  # Gentofte
    ],
    # energy_label=["A", "B"],
)

query_url = query.get_url()

# %%

response = requests.get(url=query_url)
response.raise_for_status()
result_dict = json.loads(response.text)
results = result_dict["cases"]
print(len(results))

result = results[0]
for result in results:
    municipality = result["address"]["municipality"]["name"]
    size = result.get("housingArea")
    price = result.get("priceCash")
    # print(f"{municipality}: {size} m2, {price} kr.")
# print(result)

# %%

home = Home.from_nested_dict(result)
print(home)

# %%

home.case_id
home.case_url

home.to_html()
print(home.to_text())


# %%

# polygon = "12.467721,55.768600|12.482656,55.759274|12.506124,55.758190|12.519962,55.767550|12.510944,55.778394|12.509179,55.788153|12.506264,55.797984|12.481980,55.806335|12.474718,55.817548|12.453262,55.816325|12.433050,55.812394|12.429428,55.811859|12.423876,55.811171|12.415170,55.800073|12.423254,55.788798|12.427297,55.776908|12.446732,55.771573|12.467721,55.768600"  # noqa: E501


# %%

if home.coordinates is None:
    print("Finding coordinates by Rejseplanen API")
    origin_location = Location.from_string(home.address)
else:
    origin_location = Location(
        lat=home.coordinates.lat,
        lon=home.coordinates.lon,
    )

trip_request = TripRequest(
    originCoordLat=origin_location.lat,
    originCoordLong=origin_location.lon,
    destId="8600646",  # (Nørreport st)
    # destCoordLat="55.683597",  # Destination latitude
    # destCoordLong="12.5708992",  # Destination longitude
    date="2025-05-19",  # Monday's date in YYYY-MM-DD format
    time="08:00",  # Time in hh:mm format
)
trip_response = trip_request.get_response()

journey = Journey(**trip_response)
trip1 = journey.get_fastest_trip_simple()
trip2 = journey.get_fastest_trip_corrected()

# print(trip1)
print(trip1.description)
print(trip2.description)
