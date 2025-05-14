import os
from datetime import datetime, timedelta

import requests

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def get_travel_time_distance_matrix(
    origins: str | list[str],
    destination: str,
    mode: str,
    departure_time: int,
) -> dict:
    """Get travel time between two coordinates using Google Maps Distance Matrix API."""
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    if not isinstance(origins, list):
        origins = [origins]

    params = {
        "origins": "|".join(origins),  # Join multiple origins with "|"
        "destinations": destination,
        "mode": mode,
        "departure_time": departure_time,
        "key": API_KEY,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # if data["status"] == "OK":
    #     duration = data["rows"][0]["elements"][0]["duration"]["text"]
    #     return duration
    # else:
    #     raise Exception(f"Error from Google Maps API: {data['status']}")

    if data["status"] == "OK":
        travel_times = {}
        data["origin_addresses"]
        data["rows"]
        for i, origin in enumerate(origins):
            element = data["rows"][i]["elements"][0]
            if element["status"] == "OK":
                travel_times[origin] = element["duration"]["text"]
            else:
                travel_times[origin] = f"Error: {element['status']}"
        return travel_times
    else:
        raise Exception(f"Error from Google Maps API: {data['status']}")


# Coordinates for A and B
# origin = "55.768600,12.467721"  # Replace with your origin coordinates
origins = [
    "55.768600,12.467721",  # Origin 1
    "55.759274,12.482656",  # Origin 2
    "55.758190,12.506124",  # Origin 3
]
destination = "Nørreport, Nørre Voldgade 13, 1358 København K, Denmark"

# Calculate departure time for 8:00 AM on the next Monday
now = datetime.now()
days_until_monday = (7 - now.weekday()) % 7
next_monday = now + timedelta(days=days_until_monday)
departure_time = int(
    (
        next_monday.replace(hour=8, minute=0, second=0, microsecond=0)
        - datetime(1970, 1, 1)
    ).total_seconds()
)

# Get travel times
try:
    public_transport_time = get_travel_time_distance_matrix(
        origins, destination, mode="transit", departure_time=departure_time
    )
    bike_time = get_travel_time_distance_matrix(
        origins, destination, mode="bicycling", departure_time=departure_time
    )

    print(f"Travel time by public transport: {public_transport_time}")
    print(f"Travel time by bike: {bike_time}")
except Exception as e:
    print(f"Error: {e}")
