# %%

import os
import re
from datetime import timedelta
from typing import Annotated, Any, Self

import requests
from dotenv import load_dotenv
from pydantic import AliasPath, BaseModel, BeforeValidator, Field
from rich import print

# %%

load_dotenv(dotenv_path=".env")
API_KEY = os.getenv("REJSEPLANEN_API_KEY")


# %%


class Request(BaseModel):
    """Request to the Rejseplanen API.

    For more info on inputs:    https://www.rejseplanen.dk/api/trip?wadl
    For more info on returns:   https://www.rejseplanen.dk/api/xsd/rest.xsd
    """

    accessId: str
    originCoordLat: str | None = None
    originCoordLong: str | None = None
    destId: str | None = None
    destCoordLat: str | None = None
    destCoordLong: str | None = None
    date: str | None = None
    time: str | None = None
    format: str = "json"

    base_url: str = "https://www.rejseplanen.dk/api/"
    endpoint: str = "trip"

    def get_response(self) -> dict:
        """Get the response from the API."""
        params = self.model_dump(exclude_none=True)

        # Make the GET request
        response = requests.get(self.base_url + self.endpoint, params=params)

        # Check the response status and print the result
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error: {response.status_code} {response.text}")


# Define the query parameters
params = {
    "accessId": API_KEY,  # Your API key
    "originCoordLat": "55.7855248",  # Origin latitude
    "originCoordLong": "12.464205",  # Origin latitude
    "destId": "8600646",  # (Nørreport st)
    # "destCoordLat": "55.683597",  # Destination latitude
    # "destCoordLong": "12.5708992",  # Destination longitude
    "date": "2025-05-19",  # Monday's date in YYYY-MM-DD format
    "time": "08:00",  # Time in hh:mm format
}

request = Request(**params)
response = request.get_response()


# %%


class Duration(BaseModel):
    """Duration string in the format PT23H59M0S.

    example_duration_1 = "PT43M"
    example_duration_2 = "PT23H59M0S"
    """

    dt: timedelta
    raw: str

    @property
    def minutes(self) -> float:
        """Get the duration in minutes."""
        return self.dt.total_seconds() / 60

    @classmethod
    def from_string(cls, duration_str: str) -> Self:
        """Parse a duration string in the format PT23H59M0S."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}")
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        dt = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return cls(dt=dt, raw=duration_str)


DurationFromStr = Annotated[Duration, BeforeValidator(Duration.from_string)]


# %%


class BaseLeg(BaseModel):
    Origin: dict
    Destination: dict
    id: str
    idx: int
    name: str
    type: str
    duration: DurationFromStr


class WalkLeg(BaseLeg):
    GisRef: dict
    GisRoute: dict
    dist: int


class TrainOrBusLeg(BaseLeg):
    Notes: dict | None
    JourneyDetailRef: dict | None
    JourneyStatus: str | None
    Product: list[dict] | None
    JourneyDetail: dict | None
    number: str | None
    category: str | None
    reachable: bool | None
    direction: str | None
    directionFlag: str | None
    minimumChangeDuration: str | None = None


def _ensure_proper_leg(value: Any) -> BaseLeg:  # noqa: ANN401
    try:
        leg = BaseLeg(**value)
    except Exception as e:
        raise ValueError(f"Failed to parse leg: {e}")

    if leg.type == "WALK":
        return WalkLeg(**value)
    elif leg.type == "JNY":
        return TrainOrBusLeg(**value)
    else:
        print(f"Unknown leg type: {leg.type}")
        return BaseLeg(**value)


Leg = Annotated[BaseLeg, BeforeValidator(_ensure_proper_leg)]


# %%


class Trip(BaseModel):
    Origin: dict
    Destination: dict
    legs: list[Leg] = Field(validation_alias=AliasPath("LegList", "Leg"))
    duration: DurationFromStr

    # ServiceDays: list
    # LegList: list[dict] = Field(alias="LegList.Leg")
    # TariffResult: dict
    # calculation: dict
    # TripStatus: str
    # idx: int
    # tripId: str
    # ctxRecon: str
    # checksum: str

    @property
    def duration_simple(self) -> float:
        return self.duration.minutes

    def _get_duration_corrected(
        self,
        initial_speed: float = 15,  # km/h
        extra_time: float = 1,  # minutes
    ) -> float:
        """Calculate the corrected duration of the trip.

        The corrected duration is calculated by taking the first leg of the trip
        and checking if it is a WalkLeg. If it is, the duration is corrected
        by subtracting the time it would take to bike instead of walk and adding
        the extra time for bike parking. The corrected duration is then returned.
        """
        first_leg = self.legs[0]
        if not isinstance(first_leg, WalkLeg):
            return self.duration_simple

        bike_duration = first_leg.dist / 1000 / (initial_speed / 60)
        walk_duration = first_leg.duration.minutes
        speedup = walk_duration - bike_duration
        corrected_duration = self.duration_simple - speedup + extra_time
        return corrected_duration

    @property
    def duration_corrected(self) -> float:
        return self._get_duration_corrected(initial_speed=15, extra_time=1)


# %%


class Journey(BaseModel):
    """Journey response from Rejseplanen API.

    Each journey contains multiple trips. Each trip contains multiple legs.
    The legs can be of different types, such as WalkLeg or TrainOrBusLeg.
    The duration of the trip is calculated based on the legs.
    The duration is in minutes and can be corrected based on the biking speed.
    """

    trips: list[Trip] = Field(alias="Trip")

    @property
    def best_duration_simple(self) -> float:
        """Get the best duration of the trip."""
        best_duration = min([trip.duration_simple for trip in self.trips])
        return best_duration

    @property
    def best_duration_corrected(self) -> float:
        """Get the best corrected duration of the trip."""
        best_duration = min([trip.duration_corrected for trip in self.trips])
        return best_duration


journey = Journey(**response)
trip = journey.trips[0]
print(trip)
