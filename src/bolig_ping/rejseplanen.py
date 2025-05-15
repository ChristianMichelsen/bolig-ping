"""Rejseplanen API wrapper."""

# %%

import os
import re
from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Any, Self

import requests
from dotenv import load_dotenv
from pydantic import AliasPath, BaseModel, BeforeValidator, Field, computed_field

# %%


load_dotenv(dotenv_path=".env")
API_KEY = os.getenv("REJSEPLANEN_API_KEY")
if API_KEY is None:
    raise ValueError("REJSEPLANEN_API_KEY not found in .env file. Please set it.")


# %%


class BaseRequest(BaseModel):
    """Base class for requests to the Rejseplanen API.

    For more info on returns:   https://www.rejseplanen.dk/api/xsd/rest.xsd
    """

    accessId: str = API_KEY
    endpoint: str
    format: str = "json"

    base_url: str = "https://www.rejseplanen.dk/api/"

    @property
    def params(self) -> dict:
        """Get the parameters for the request."""
        params = self.model_dump(exclude_none=True)
        return params

    def get_response(self) -> dict:
        """Get the response from the API."""
        # Make the GET request
        response = requests.get(self.base_url + self.endpoint, params=self.params)

        # Check the response status and print the result
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error: {response.status_code} {response.text}")


# %%


class LocationRequest(BaseRequest):
    """Request to the Rejseplanen API.

    For more info on inputs:    https://www.rejseplanen.dk/api/location.name?wadl
    For more info on returns:   https://www.rejseplanen.dk/api/xsd/rest.xsd
    """

    input: str
    endpoint: str = "location.name"
    maxNo: int = 1


class Location(BaseModel):
    """Location name response from Rejseplanen API."""

    extId: str | None = None
    name: str | None = None
    lon: float
    lat: float

    @classmethod
    def from_string(cls, location_string: str) -> Self:
        """Get the location from the Rejsekort API."""
        request = LocationRequest(input=location_string)
        response = request.get_response()
        location_data = response["stopLocationOrCoordLocation"][0]["CoordLocation"]
        return cls(**location_data)


# %%


class TripRequest(BaseRequest):
    """Request to the Rejseplanen API.

    For more info on inputs:    https://www.rejseplanen.dk/api/trip?wadl
    For more info on returns:   https://www.rejseplanen.dk/api/xsd/rest.xsd
    """

    originId: str | None = None
    originCoordLat: float | None = None
    originCoordLong: float | None = None
    destId: str | None = None
    destCoordLat: float | None = None
    destCoordLong: float | None = None
    date: str | None = None
    time: str | None = None
    endpoint: str = "trip"


# %%

# %%


class Duration(BaseModel):
    """Duration string in the format PT23H59M0S.

    example_duration_1 = "PT43M"
    example_duration_2 = "PT23H59M0S"
    """

    dt: timedelta
    raw: str

    @computed_field
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


class TransportationMethod(StrEnum):
    """Enum for transportation methods."""

    WALK = "prod_walk"
    BUS = "prod_bus"
    METRO = "prod_sub"
    S_TRAIN = "prod_comm"
    REGIONAL_TRAIN = "prod_ic"
    LOCAL_TRAIN = "prod_lokalbane"


class LegProductIcon(BaseModel):
    """Model class for the product icon of a single leg."""

    res: str


class LegProduct(BaseModel):
    """Model class for the product of a single leg."""

    icon: LegProductIcon
    name: str
    internalName: str


class BaseLeg(BaseModel):
    """Base class for a leg of a trip."""

    Origin: dict
    Destination: dict
    id: str
    idx: int
    name: str
    type: str
    duration: DurationFromStr
    product: LegProduct = Field(validation_alias=AliasPath("Product", 0))

    @computed_field
    @property
    def method(self) -> TransportationMethod:
        """Get the method of transport."""
        method = self.product.icon.res
        return TransportationMethod(method)


class WalkLeg(BaseLeg):
    """A leg of a trip that is a walk."""

    GisRef: dict
    GisRoute: dict
    dist: int


class JNYLeg(BaseLeg):
    """A leg of a trip that is a public transport journey.

    JNY = Public Transport
    """

    JourneyDetailRef: dict | None
    JourneyStatus: str | None
    JourneyDetail: dict | None
    number: str | None
    category: str | None
    reachable: bool | None
    direction: str | None
    directionFlag: str | None
    Notes: dict | None = None
    minimumChangeDuration: str | None = None


def _ensure_proper_leg(raw_leg: Any) -> BaseLeg:  # noqa: ANN401
    try:
        leg = BaseLeg(**raw_leg)
    except Exception as e:
        raise ValueError(f"Failed to parse leg: {e}")

    if leg.method == "prod_walk":
        return WalkLeg(**raw_leg)

    return JNYLeg(**raw_leg)


Leg = Annotated[BaseLeg, BeforeValidator(_ensure_proper_leg)]

# %%


class Trip(BaseModel):
    """Trip response from Rejseplanen API."""

    Origin: dict
    Destination: dict
    legs: list[Leg] = Field(validation_alias=AliasPath("LegList", "Leg"))
    duration: DurationFromStr

    @computed_field
    @property
    def mode_changes(self) -> float:
        """Get the number of mode changes in the trip."""
        return len(self.legs) - 1

    @computed_field
    @property
    def duration_simple(self) -> float:
        """Get the simple duration of the trip."""
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

        # Bike instead of walk
        bike_duration = first_leg.dist / 1000 / (initial_speed / 60)
        walk_duration = first_leg.duration.minutes
        speedup = walk_duration - bike_duration
        corrected_duration = self.duration_simple - speedup + extra_time
        return corrected_duration

    @computed_field
    @property
    def duration_corrected(self) -> float:
        """Get the corrected duration of the trip."""
        return self._get_duration_corrected(initial_speed=15, extra_time=1)

    @property
    def methods(self) -> list[TransportationMethod]:
        """Get the methods of transport for the trip."""
        return [leg.method for leg in self.legs]

    @property
    def description(self) -> str:
        """Get a description of the trip."""
        description = "Trip description: \n"
        for i, leg in enumerate(self.legs, start=1):
            origin_name = leg.Origin["name"]
            destination_name = leg.Destination["name"]
            s_method = leg.method.name.capitalize().replace("_", "-")
            duration = leg.duration.minutes
            description += (
                f"\t{i}) {s_method}"
                f" from {origin_name} to {destination_name}"
                f" ({duration:.0f} min)\n"
            )
        description += (
            f"Total duration: {self.duration_simple:.0f} min"
            f" ({self.duration_corrected:.0f} if biking instead of walking first) "
        )
        return description


# %%


class Journey(BaseModel):
    """Journey response from Rejseplanen API.

    Each journey contains multiple trips. Each trip contains multiple legs.
    The legs can be of different types, such as WalkLeg or TrainOrBusLeg.
    The duration of the trip is calculated based on the legs.
    The duration is in minutes and can be corrected based on the biking speed.
    """

    trips: list[Trip] = Field(alias="Trip")

    @computed_field
    @property
    def best_duration_simple(self) -> float:
        """Get the best duration of the trip."""
        best_duration = min([trip.duration_simple for trip in self.trips])
        return best_duration

    @computed_field
    @property
    def best_duration_corrected(self) -> float:
        """Get the best corrected duration of the trip."""
        best_duration = min([trip.duration_corrected for trip in self.trips])
        return best_duration

    def get_fastest_trip_simple(self) -> Trip:
        """Get the fastest trip based on the simple duration."""
        fastest_trip = min(self.trips, key=lambda trip: trip.duration_simple)
        return fastest_trip

    def get_fastest_trip_corrected(self) -> Trip:
        """Get the fastest trip based on the corrected duration."""
        fastest_trip = min(self.trips, key=lambda trip: trip.duration_corrected)
        return fastest_trip
