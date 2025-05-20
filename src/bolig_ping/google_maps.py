"""Google Maps API wrapper."""

# %%

import os
from datetime import datetime
from enum import StrEnum, auto

import requests
from dotenv import load_dotenv
from pydantic import AliasPath, BaseModel, Field, computed_field

# %%

load_dotenv(dotenv_path=".env")
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if API_KEY is None:
    raise ValueError("GOOGLE_MAPS_API_KEY not found in .env file. Please set it.")

# %%


class TravelMode(StrEnum):
    """Enum for travel modes.

    Follow: https://developers.google.com/maps/documentation/distance-matrix/distance-matrix#mode
    """

    DRIVING = auto()
    WALKING = auto()
    BIKING = "bicycling"
    TRANSIT = auto()


# %%


class BaseTravelTime(BaseModel):
    """Base class for travel time."""

    duration_seconds: float
    distance_meters: float
    status: str = Field(repr=False)

    @computed_field
    @property
    def distance(self) -> float:
        """Get distance in kilometers."""
        return self.distance_meters / 1000

    @computed_field
    @property
    def duration(self) -> float:
        """Get duration in minutes."""
        return self.duration_seconds / 60


class TravelTime(BaseTravelTime):
    """Travel time between two coordinates.

    Works when a single origin and a single destination are provided.
    """

    origin: str = Field(validation_alias=AliasPath("origin_addresses", 0))
    destination: str = Field(validation_alias=AliasPath("destination_addresses", 0))
    distance_meters: float = Field(
        repr=False,
        validation_alias=AliasPath("rows", 0, "elements", 0, "distance", "value"),
    )
    distance_text: str = Field(
        repr=False,
        validation_alias=AliasPath("rows", 0, "elements", 0, "distance", "text"),
    )
    duration_seconds: float = Field(
        repr=False,
        validation_alias=AliasPath("rows", 0, "elements", 0, "duration", "value"),
    )
    duration_text: str = Field(
        repr=False,
        validation_alias=AliasPath("rows", 0, "elements", 0, "duration", "text"),
    )


# %%


class TravelTimeElement(BaseTravelTime):
    """Travel time element between two coordinates."""

    distance_meters: float = Field(
        repr=False, validation_alias=AliasPath("distance", "value")
    )
    distance_text: str = Field(
        repr=False, validation_alias=AliasPath("distance", "text")
    )
    duration_seconds: float = Field(
        repr=False, validation_alias=AliasPath("duration", "value")
    )
    duration_text: str = Field(
        repr=False, validation_alias=AliasPath("duration", "text")
    )


class TravelTimeRow(BaseModel):
    """Helper class for travel time matrix."""

    elements: list[TravelTimeElement]


class TravelTimeMatrix(BaseModel):
    """Travel time matrix between multiple origins and destinations.

    Works when multiple origins and multiple destinations are provided.
    """

    destination_addresses: list[str]
    origin_addresses: list[str]
    rows: list[TravelTimeRow]
    status: str


# %%


class Timestamp(BaseModel):
    """Get a the proper Timestamp time.

    A timestamp time is the integer number of seconds since midnight,
    January 1, 1970 UTC.
    """

    @classmethod
    def from_datetime(cls, dt: datetime) -> int:
        """Convert a datetime object to seconds since epoch."""
        return int(dt.timestamp())

    @classmethod
    def from_now(cls) -> int:
        """Get the current timestamp in seconds since epoch."""
        now = datetime.now()
        return cls.from_datetime(now)

    @classmethod
    def from_string(cls, dt_str: str) -> int:
        """Convert a string to a timestamp."""
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return cls.from_datetime(dt)

    @classmethod
    def parse(cls, value: datetime | str | float | int) -> int:
        """Parse a value to a timestamp."""
        if isinstance(value, datetime):
            return cls.from_datetime(value)
        elif isinstance(value, str):
            return cls.from_string(value)
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, int):
            return value
        else:
            raise ValueError(
                f"Invalid value type. Must be datetime, str, or int, got {type(value)}"
            )


# %%


def get_travel_time(
    origin: str,
    destination: str,
    mode: TravelMode,
    departure_time: datetime | str | float | int | None = None,
) -> TravelTime:
    """Get travel time between two coordinates using Google Maps Distance Matrix API."""
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    if departure_time is not None:
        # Convert datetime to seconds since epoch
        departure_time = Timestamp.parse(departure_time)

    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "departure_time": departure_time,
        "key": API_KEY,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    travel_time = TravelTime.model_validate(data)
    if not travel_time.status == "OK":
        raise ValueError(f"Error: {travel_time.status}")
    return travel_time


def get_bike_time(
    origin: str,
    destination: str,
    departure_time: datetime | str | float | int | None = None,
) -> TravelTime:
    """Get bike time between two coordinates using Google Maps Distance Matrix API."""
    return get_travel_time(
        origin=origin,
        destination=destination,
        mode=TravelMode.BIKING,
        departure_time=departure_time,
    )


def get_walk_time(
    origin: str,
    destination: str,
    departure_time: datetime | str | float | int | None = None,
) -> TravelTime:
    """Get walk time between two coordinates using Google Maps Distance Matrix API."""
    return get_travel_time(
        origin=origin,
        destination=destination,
        mode=TravelMode.WALKING,
        departure_time=departure_time,
    )


# %%


def get_travel_time_distance_matrix(
    origins: list[str],
    destinations: list[str],
    mode: TravelMode = TravelMode.DRIVING,
    departure_time: datetime | str | float | int | None = None,
) -> TravelTimeMatrix:
    """Get travel time between two coordinates using Google Maps Distance Matrix API."""
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    if departure_time is not None:
        # Convert datetime to seconds since epoch
        departure_time = Timestamp.parse(departure_time)

    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "mode": mode,
        "departure_time": departure_time,
        "key": API_KEY,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    travel_matrix = TravelTimeMatrix.model_validate(data)
    return travel_matrix
