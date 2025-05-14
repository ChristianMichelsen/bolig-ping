# %%

import os
import re
from datetime import timedelta

import requests
from dotenv import load_dotenv
from rich import print

load_dotenv(dotenv_path=".env")


API_KEY = os.getenv("REJSEPLANEN_API_KEY")


# %%

# Define the base URL and endpoint
base_url = "https://www.rejseplanen.dk/api/"
endpoint = "trip"

# Define the query parameters
params = {
    "accessId": API_KEY,  # Your API key
    "originCoordLat": "55.7855248",  # Origin latitude
    "originCoordLong": "12.464205",  # Origin latitude
    "destCoordLat": "55.683597",  # Destination latitude
    "destCoordLong": "12.5708992",  # Destination longitude
    "date": "2025-05-19",  # Monday's date in YYYY-MM-DD format
    "time": "08:00",  # Time in hh:mm format
    "format": "json",  # Requesting JSON response
    "originBike": True,  # Origin bike parameter
    "originCar": True,
}


# Make the GET request
response = requests.get(base_url + endpoint, params=params)

# Check the response status and print the result
if response.status_code == 200:
    # print("Response JSON:", response.json())
    data = response.json()
else:
    print("Error:", response.status_code, response.text)


# %%

# print(data)
data.keys()
# [
#     "Trip",
#     "ResultStatus",
#     "TechnicalMessages",
#     "serverVersion",
#     "dialectVersion",
#     "planRtTs",
#     "requestId",
#     "scrB",
#     "scrF",
# ]

len(data["Trip"])  # 5
data["Trip"][0].keys()
# [
#     "Origin",
#     "Destination",
#     "ServiceDays",
#     "LegList",
#     "TariffResult",
#     "calculation",
#     "TripStatus",
#     "idx",
#     "tripId",
#     "ctxRecon",
#     "duration",
#     "checksum",
# ]

data["Trip"][0]["Origin"]
# data["Trip"][0]["Origin"]["time"]
# data["Trip"][0]["Origin"]["date"]

data["Trip"][0]["Destination"]

# data["Trip"][0]["ServiceDays"]

len(data["Trip"][0]["LegList"]["Leg"])  # 3
data["Trip"][0]["LegList"]["Leg"][0]  # one for each leg
data["Trip"][0]["LegList"]["Leg"][1]
data["Trip"][0]["LegList"]["Leg"][2]

# data["Trip"][0]["TariffResult"]
# data["Trip"][0]["calculation"]
# data["Trip"][0]["TripStatus"]
# data["Trip"][0]["idx"]
# data["Trip"][0]["tripId"]
# data["Trip"][0]["ctxRecon"]

data["Trip"][0]["duration"]  # PT43M
data["Trip"][1]["duration"]  # PT39M
data["Trip"][2]["duration"]  # PT43M
data["Trip"][3]["duration"]  # PT43M
data["Trip"][4]["duration"]  # PT39M

# PT23H59M0S

# %%

data["Trip"][4]["LegList"]["Leg"][0]
data["Trip"][4]["LegList"]["Leg"][1]
data["Trip"][4]["LegList"]["Leg"][2]
data["Trip"][4]["LegList"]["Leg"][3]
data["Trip"][4]["LegList"]["Leg"][4]


# %%


trip_i = 2
data["Trip"][trip_i]["LegList"]["Leg"][0]
data["Trip"][trip_i]["LegList"]["Leg"][0]["type"]
data["Trip"][trip_i]["LegList"]["Leg"][0]["duration"]
data["Trip"][trip_i]["LegList"]["Leg"][0]["dist"]

# (507 / 1000) / (7 / 60)  # km / h
# (1665 / 1000) / (21 / 60)  # km / h


def get_duration_simple(data: dict) -> float:
    duration_str = data["Trip"][0]["duration"]
    return parse_duration_to_minutes(duration_str)


def get_duration_by_legs(data: dict) -> float:
    total = 0
    for leg in data["Trip"][0]["LegList"]["Leg"]:
        leg_duration_str = leg["duration"]
        leg_duration = parse_duration_to_minutes(leg_duration_str)
        total += leg_duration
    return total


def get_duration_corrected(
    data: dict,
    initial_speed: float = 15,  # km/h
) -> float:
    total = 0
    for i, leg in enumerate(data["Trip"][0]["LegList"]["Leg"]):
        if i == 0 and leg["type"] == "WALK":
            dist = leg["dist"]
            corrected_duration = dist / 1000 / (initial_speed / 60)
            total += corrected_duration
        else:
            leg_duration_str = leg["duration"]
            leg_duration = parse_duration_to_minutes(leg_duration_str)
            total += leg_duration
    return total


# %%

get_duration_simple(data)
get_duration_by_legs(data)
get_duration_corrected(data, initial_speed=15)  # 23.5 km/h
get_duration_corrected(data, initial_speed=5)  # 23.5 km/h


# %%


def parse_duration_to_dt(duration_str: str) -> timedelta:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def parse_duration_to_minutes(duration_str: str) -> float:
    dt = parse_duration_to_dt(duration_str)
    return dt.total_seconds() / 60


# Example usage
example_duration_1 = "PT43M"
example_duration_2 = "PT23H59M0S"

print(parse_duration_to_minutes(example_duration_1))  # Output: (0, 43, 0)
print(parse_duration_to_minutes(example_duration_2))  # Output: (23, 59, 0)
