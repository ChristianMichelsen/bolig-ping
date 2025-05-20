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

    For more info:  https://www.rejseplanen.dk/api/xsd/
                    https://www.rejseplanen.dk/api/swagger-ui
                    https://www.rejseplanen.dk/api/api-doc
                    https://labs.rejseplanen.dk/hc/da/article_attachments/22429062830237


    Authentication:
        Every client using the API needs to pass a valid authentication key
        in every request. The authentication key can be passed either as
        parameter in the URL:
            accessId=<your_key_here>
        or by using the Authorization Header like this:
            Authorization: Bearer <your_key_here>
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



    originBike:

        To enable bike, minimum distance
        should be zero meters, maximum
        distance should be 1000 meters set the
        parameter originBike=1,0,1000.

        If the default distance should be used,
        just put no value, e.g 1,,1500 to have
        bike enabled, default minimum and 1500
        meters as maximum.

        Other possible settings are
        Speed
            < 100: faster
            = 100: normal (default)
            > 100: slower

        Be faster than normal: 1,0,1000,50

        Be slower than normal: 1,0,1000,150

        Bee line calculation: 0 (default) or 1


    rtMode:
        Set the realtime mode to be used.

        OFF:
            Search on planned data, ignore
            real-time information completely:
            Connections are computed on the basis
            of planned data. No real-time
            information is shown.
        INFOS:
            Search on planned data, use
            real-time information for display only:
            Connections are computed on the basis
            of planned data. Delays and feasibility of
            the connections are integrated into the
            result. Note that additional trains
            (supplied via realtime feed) will not be
            part of the resulting connections.
        FULL:
            Combined search on planned and real-time data
            This search consists of two steps:
            i.
                Search on scheduled data
            ii.
                If the result of step (i) contains a nonfeasible connection,
                a search on realtime data is performed and all results are combined.
        REALTIME:
            Search on real-time data:
            Connections are computed on the basis
            of real-time data, using planned
            schedule only whenever no real-time
            data is available. All connections
            computed are feasible with respect to
            the currently known real-time situation.
            Additional trains (supplied via real-time
            feed) will be found if these are part of a
            fast, comfortable, or direct connection
            (or economic connection, if economic
            search is activated).
        SERVER_DEFAULT:
            one of the above configured in the HAFAS server back end.
    """

    originId: str | None = None
    originCoordLat: float | None = None
    originCoordLong: float | None = None
    originBike: str | None = None

    destId: str | None = None
    destCoordLat: float | None = None
    destCoordLong: float | None = None
    date: str | None = None  # "YYYY-MM-DD"
    time: str | None = None  # "hh:mm[:ss]". Seconds will be ignored for requests
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
    BIKE = "prod_bike"
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


class BikeLeg(BaseLeg):
    """A leg of a trip that is by bike."""

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

    if leg.method == TransportationMethod.WALK:
        return WalkLeg(**raw_leg)

    elif leg.method == TransportationMethod.BIKE:
        return BikeLeg(**raw_leg)

    return JNYLeg(**raw_leg)


Leg = Annotated[BaseLeg, BeforeValidator(_ensure_proper_leg)]

# %%


class Trip(BaseModel):
    """Trip response from Rejseplanen API."""

    Origin: dict
    Destination: dict
    legs: list[Leg] = Field(validation_alias=AliasPath("LegList", "Leg"))
    duration_str: DurationFromStr = Field(validation_alias="duration")

    @computed_field
    @property
    def mode_changes(self) -> float:
        """Get the number of mode changes in the trip."""
        return len(self.legs) - 1

    @computed_field
    @property
    def duration(self) -> float:
        """Get the duration of the trip in minutes."""
        return self.duration_str.minutes

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
        description += f"Total duration: {self.duration:.0f} min"
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
    def shortest_duration(self) -> float:
        """Get the shortest duration of the trip."""
        shortest_duration = min([trip.duration for trip in self.trips])
        return shortest_duration

    def get_fastest_trip(self) -> Trip:
        """Get the fastest trip based on the simple duration."""
        fastest_trip = min(self.trips, key=lambda trip: trip.duration)
        return fastest_trip
