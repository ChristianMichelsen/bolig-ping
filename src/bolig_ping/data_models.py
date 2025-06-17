"""Data models used in the project."""

import datetime
import json
import logging
from functools import cache
from pathlib import Path
from typing import Literal, Self

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, computed_field, field_serializer, field_validator
from retry_reloaded import retry
from tqdm.auto import tqdm

from bolig_ping import gis_schools, google_maps, rejseplanen
from bolig_ping.gis_noise import GisNoise, Noise
from bolig_ping.gis_schools import GisSchools
from bolig_ping.google_maps import get_bike_time

# %%

logger = logging.getLogger(__package__)

GIS_DIR = Path("data") / "gis"


# %%


ADDRESS_TYPES_MAP = {
    "villa": "villa",
    "rækkehus": "terraced house",
    "andelslejlighed": "cooperative",
    "helårsgrund": "full year plot",
    "fritidsgrund": "holiday plot",
    "ejerlejlighed": "condo",
    "fritidsbolig": "holiday house",
    "landejendom": "farm,hobby farm",
    "villalejlighed": "villa apartment",
    "husbåd": "houseboat",
}
ADDRESS_TYPES_MAP_INVERSE = {v: k for k, v in ADDRESS_TYPES_MAP.items()}


AddressType = Literal[
    "villa",
    "rækkehus",
    "andelslejlighed",
    "helårsgrund",
    "fritidsgrund",
    "ejerlejlighed",
    "fritidsbolig",
    "landejendom",
    "villalejlighed",
    "husbåd",
]


ENERGY_LABELS = Literal[
    "A2020",
    "A2015",
    "A2010",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
]


# %%


class SearchQuery(BaseModel):
    """A search query for the Boligsiden API."""

    # Boligtype
    address_type: list[AddressType] = Field(
        serialization_alias="addressTypes",
    )
    # Kommune
    municipality: list[str] = Field(
        serialization_alias="municipalities",
    )
    # Pris
    min_price: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="priceMin",
    )
    # Pris
    max_price: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="priceMax",
    )
    # Størrelse
    min_size: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="areaMin",
    )
    # Størrelse
    max_size: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="areaMax",
    )
    # Månedlig udgift
    min_monthly_fee: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="monthlyExpenseMin",
    )
    # Månedlig udgift
    max_monthly_fee: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="monthlyExpenseMax",
    )
    # Antal værelser
    min_rooms: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="numberOfRoomsMin",
    )
    # Antal værelser
    max_rooms: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="numberOfRoomsMax",
    )
    # By
    city: list[str] | None = Field(
        default=None,
        serialization_alias="cities",
    )
    # Energimærke
    energy_label: list[ENERGY_LABELS] | None = Field(
        default=None,
        serialization_alias="energyLabels",
    )
    # Fritekstsøgning
    freetext: list[str] | None = Field(
        default=None,
        serialization_alias="freeText",
    )
    # Plan
    min_levels: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="levelsMin",
    )
    # Plan
    max_levels: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="levelsMax",
    )
    # Etage
    min_floor: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="floorMin",
    )
    # Etage
    max_floor: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="floorMin",
    )
    # Grundareal
    min_lot_area: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="lotAreaMin",
    )
    # Grundareal
    max_lot_area: int | None = Field(
        default=None,
        ge=1,
        serialization_alias="lotAreaMax",
    )
    # Byggeår
    min_year_built: int | None = Field(
        default=None,
        ge=1500,
        serialization_alias="yearBuiltFrom",
    )
    # Byggeår
    max_year_built: int | None = Field(
        default=None,
        ge=1500,
        serialization_alias="yearBuiltTo",
    )
    # Dage til salg
    min_time_on_market: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="timeOnMarketMin",
    )
    # Dage til salg
    max_time_on_market: int | None = Field(
        default=None,
        ge=0,
        serialization_alias="timeOnMarketMax",
    )
    # Projektsalg
    is_project: bool | None = Field(
        default=None,
        serialization_alias="presale",
    )
    # Kælder
    has_basement: bool | None = Field(
        default=None,
        serialization_alias="filterBasement",
    )
    # Åbent hus
    has_open_house: bool | None = Field(
        default=None,
        serialization_alias="filterOpenHouse",
    )
    # Elevator
    has_elevator: bool | None = Field(
        default=None,
        serialization_alias="elevator",
    )
    # Prisfald
    has_price_drop: bool | None = Field(
        default=None,
        serialization_alias="filterPriceDrop",
    )
    # Altan
    has_balcony: bool | None = Field(
        default=None,
        serialization_alias="balcony",
    )
    # Terasse
    has_terrace: bool | None = Field(
        default=None,
        serialization_alias="terrace",
    )
    # Geografisk søgning ud fra polygon, fx:
    # "12.4,55.7|12.6,55.7|12.5,55.8|12.4,55.7
    polygon: str | None = None
    # Geografisk søgning ud fra radius, fx:
    # "4027|12.505448,55.785400", meter|coords
    radius: str | None = None

    @field_serializer("address_type")
    def serialize_address_type(
        self,
        address_type: list[AddressType],
    ) -> str:
        """Serialize the address_type."""
        return ",".join(ADDRESS_TYPES_MAP[atype] for atype in address_type)

    @field_serializer("energy_label")
    def serialize_energy_label(
        self,
        energy_label: list[ENERGY_LABELS],
    ) -> str:
        """Serialize the energy label."""
        return ",".join(energy_label)

    def export_to_dict(self, by_alias: bool = False) -> dict:
        """Get the search query as a dictionary.

        Returns:
            The search query as a dictionary.
        """
        return self.model_dump(exclude_none=True, by_alias=by_alias)

    def is_empty(self) -> bool:
        """Check if the search query is empty.

        Returns:
            True if the search query is empty, False otherwise.
        """
        return len(self.export_to_dict()) == 0

    def get_url(self, page: int = 1) -> str:
        """Get the URL for the search query.

        Args:
            page (optional):
                The page number to get the URL for. Defaults to 1.

        Returns:
            The URL for the search query.
        """
        url = f"https://api.boligsiden.dk/search/cases?page={page}"

        as_dict = self.export_to_dict(by_alias=True)

        for key, value in as_dict.items():
            if not isinstance(value, list):
                value = [value]
            for item in value:
                url += f"&{key}={item}"

        return url

    def _results_to_homes(self, results: list[dict]) -> list["Home"]:
        homes: list[Home] = []
        for result in results:
            try:
                home = Home.from_nested_dict(result)
                if home.address_type in self.address_type:
                    homes.append(home)
                else:
                    logger.warning(
                        f"Address type {home.address_type} not in {self.address_type}"
                    )
            except Exception as e:
                logger.warning(f"Could not parse result {result['caseUrl']}: {e}")
                continue
        return homes

    def get_homes(self) -> list["Home"] | None:
        """Get the results for the search query.

        Returns:
            The results for the search query.
        """
        if self.is_empty():
            return None

        response = requests.get(url=self.get_url())
        response.raise_for_status()
        result_dict = json.loads(response.text)
        results = result_dict["cases"]
        if results is None:
            return None

        num_results = result_dict["totalHits"]
        num_pages = num_results // len(results)
        if num_results % len(results) != 0:
            num_pages += 1

        homes = self._results_to_homes(results)

        # Scrape the remaining pages
        if num_pages > 1:
            desc = "Scraping homes from boligsiden.dk"
            with tqdm(desc=desc, total=num_results) as pbar:
                pbar.update(len(homes))
                for page_idx in range(2, num_pages + 1):
                    url = self.get_url(page=page_idx)
                    response = requests.get(url=url)
                    response.raise_for_status()
                    result_dict = json.loads(response.text)
                    results = result_dict["cases"]
                    new_homes = self._results_to_homes(results)
                    homes.extend(new_homes)
                    homes = list(set(homes))
                    pbar.update(len(new_homes))

            # Ensure that the progress bar is at 100% at the end
            pbar.n = pbar.total

        return homes


# %%


def get_description_from_result(result: dict) -> str | None:
    """Get the description from a search result."""
    case_url = result["caseUrl"]

    response = requests.get(case_url)
    if response.ok:
        soup = BeautifulSoup(response.content, "html.parser")
        lines = soup.text.split("\n")
        long_lines = [line.strip() for line in lines if len(line.strip()) > 200]
        if long_lines:
            return "\n".join(long_lines)
        else:
            logger.warning(
                f"Could not find description for property {case_url}. The longest "
                f"line was {max(len(line) for line in lines)} characters long."
            )
    return None


# %%


class Coordinates(BaseModel):
    """Coordinates for a location."""

    lat: float
    lon: float

    @computed_field
    @property
    def coords(self) -> str:
        """Get the coordinates as a string.

        Returns:
            The coordinates as a string.
        """
        return f"{self.lat},{self.lon}"


class SearchImage(BaseModel):
    """An image from the Boligsiden API."""

    url: str
    text: str | None = Field(default=None, alias="alt")
    size: dict


# %%


@cache
def get_gis_noise(gis_dir: Path) -> GisNoise:
    """Get GIS noise data with caching."""
    gis_noise = GisNoise.from_dir(gis_dir=gis_dir)
    return gis_noise


@cache
def get_gis_schools(
    gis_dir: Path,
    municipalities: list[str],
) -> GisSchools:
    """Get GIS school data with caching."""
    gis_schools = GisSchools.from_dir(gis_dir=gis_dir, municipalities=municipalities)
    return gis_schools


# %%


def dk_format(value: int | float) -> str:
    """Format a number in Danish format."""
    return f"{value:,.0f}".replace(",", ".")


# %%


class BaseHome(BaseModel):
    """Base class for a home.

    Both Home and FlatHome inherit from this class.
    """

    road_name: str
    road_number: str | None
    floor: str | None
    door: str | None
    post_code: int
    city: str
    price: float
    num_rooms: int | None = Field(ge=1)
    size: int | None = Field(ge=1)
    monthly_fee: int | None = Field(ge=0)
    year: int | None = Field(ge=1500)
    time_on_market: int
    bathrooms: int | None = Field(ge=0)
    toilets: int | None = Field(ge=0)
    floors: int | None = Field(ge=0)
    energy_label: ENERGY_LABELS | None
    per_area_price: float = Field(ge=0)
    address_type: AddressType | None
    basement_area: int | None = Field(ge=0)
    case_id: str
    case_url: str
    title: str | None = None
    lot_area: int | None = Field(default=None, ge=0)
    weighted_area: float | None = Field(ge=0)
    price_change_percentage: float | None = None
    last_updated: datetime.date


class FlatHome(BaseHome):
    """A 'flat' home with all the data in a single object.

    This object is used for exporting the data to a CSV file.
    """

    address: str
    coord_lat: float | None = None
    coord_lon: float | None = None
    trip_duration: float | None = None
    trip_changes: int | None = None
    trip_methods: str | None = None
    trip_description: str | None = None
    noise_dB_min: float | None = None
    noise_dB_max: float | None = None
    school_name: str | None = None
    school_bike_distance: float | None = None
    school_bike_duration: float | None = None
    raw_json: str = Field(repr=False)

    def _get_components(self) -> list[str]:
        components = []
        components.append(
            f"Pris: {dk_format(self.price)} kr."
            f" ({dk_format(self.per_area_price)} kr./m²)"
        )
        if self.address_type is not None:
            components.append(f"Boligtype: {self.address_type}")
        if self.num_rooms is not None:
            components.append(
                f"Antal værelser: {self.num_rooms}"
                f" ({self.bathrooms} badeværelser, {self.toilets} toiletter)"
            )
        if self.size is not None:
            components.append(f"Boligareal: {self.size} m²")
        if self.basement_area is not None:
            components[-1] += f"(kælder: {self.basement_area} m²)"
        if self.trip_duration is not None:
            components.append(f"Rejsetid: {self.trip_duration:.0f} min")
        if self.energy_label is not None:
            components.append(f"Energimærke: {self.energy_label}")
        if self.year is not None:
            components.append(f"Bygget: {self.year}")
        if self.time_on_market is not None:
            components.append(f"Liggetid: {self.time_on_market} dage")
        if self.monthly_fee is not None:
            components.append(
                f"Mdl. ejerudgifter: {dk_format(self.monthly_fee)} kr./md"
            )
        if self.noise_dB_min is not None or self.noise_dB_max is not None:
            components.append(f"Støj: {self.noise_dB_min} - {self.noise_dB_max} dB")
        if (
            self.school_name is not None
            and self.school_bike_duration is not None
            and self.school_bike_distance is not None
        ):
            components.append(
                f"Skole: {self.school_name}"
                f" ({self.school_bike_distance:.1f} km"
                f", {self.school_bike_duration:.0f} min)"
            )
        if self.title is not None:
            components.append(f"Titel: {self.title}")

        return components

    def to_text(self) -> str:
        """Get the home as a text string.

        Returns:
            The home as a text string.
        """
        components = [f"URL: {self.case_url}", f"Addresse: {self.address}"]
        components += self._get_components()
        return "\n".join(components)


class Home(BaseHome):
    """A search result from the Boligsiden API."""

    coordinates: Coordinates | None
    image: SearchImage | None = Field(exclude=True)
    # GIS extended data
    origin_location: rejseplanen.Location | None = None
    journey: rejseplanen.Journey | None = None
    trip: rejseplanen.Trip | None = None
    noise: Noise | None = None
    school: gis_schools.School | None = None
    school_travel_time: google_maps.TravelTime | None = None
    raw_json: str = Field(repr=False)

    @classmethod
    def from_nested_dict(cls, result: dict) -> Self:
        """Create a SearchResult from a nested dictionary."""
        return cls(
            road_name=result["address"]["roadName"],
            road_number=result["address"].get("houseNumber"),
            floor=result["address"].get("floor"),
            door=result["address"].get("door"),
            post_code=result["address"].get("zipCode"),
            city=result["address"]["cityName"],
            price=result["priceCash"],
            num_rooms=result.get("numberOfRooms"),
            size=result.get("housingArea"),
            monthly_fee=result.get("monthlyExpense"),
            year=result.get("yearBuilt"),
            time_on_market=result["timeOnMarket"]["current"]["days"],
            bathrooms=result.get("numberOfBathrooms"),
            toilets=result.get("numberOfToilets"),
            floors=result.get("numberOfFloors"),
            energy_label=result.get("energyLabel"),
            per_area_price=result["perAreaPrice"],
            coordinates=Coordinates(
                lat=result["coordinates"]["lat"],
                lon=result["coordinates"]["lon"],
            ),
            address_type=result.get("addressType"),
            basement_area=result.get("basementArea"),
            case_id=result["caseID"],
            case_url=result["caseUrl"],
            title=result.get("descriptionTitle"),
            lot_area=result.get("lotArea"),
            weighted_area=result.get("weightedArea"),
            image=sorted(
                result["defaultImage"]["imageSources"],
                key=lambda img: img["size"]["height"],
                reverse=True,
            )[0],
            price_change_percentage=result.get("priceChangePercentage"),
            last_updated=datetime.date.today(),
            raw_json=json.dumps(result),
        )

    @field_validator("energy_label", mode="before")
    @classmethod
    def energy_label_to_upper(cls, energy_label: str | None) -> str | None:
        """Convert the energy label to uppercase."""
        if isinstance(energy_label, str):
            return energy_label.upper()
        elif energy_label is None:
            return None
        raise ValueError(
            f"Invalid energy label: {energy_label}. Must be a string or None."
        )

    @field_validator("address_type", mode="before")
    @classmethod
    def transform_address_type(cls, address_type: str | None) -> str | None:
        """Translate the address type to Danish."""
        if isinstance(address_type, str):
            return ADDRESS_TYPES_MAP_INVERSE[address_type]
        elif address_type is None:
            return None
        raise ValueError(
            f"Invalid address type: {address_type}. Must be a string or None."
        )

    @computed_field
    @property
    def address(self) -> str:
        """Get the address of the home.

        Returns:
            The address of the home.
        """
        address = self.road_name
        if self.road_number:
            address += f" {self.road_number}"
        if self.floor:
            floor = self.floor.replace("0", "st.")
            address += f" {floor}"
        if self.door:
            address += f" {self.door}"
        if self.post_code:
            address += f" {self.post_code}"
        if self.city:
            address += f" {self.city}"
        return address

    def __hash__(self) -> int:
        """Get the hash of the home.

        Returns:
            The hash of the home.
        """
        return hash(self.case_url)

    def _get_components(self) -> list[str]:
        components = []
        components.append(
            f"Pris: {dk_format(self.price)} kr."
            f" ({dk_format(self.per_area_price)} kr./m²)"
        )
        if self.num_rooms is not None:
            components.append(
                f"Antal værelser: {self.num_rooms}"
                f" ({self.bathrooms} badeværelser, {self.toilets} toiletter)"
            )
        if self.size is not None:
            components.append(f"Boligareal: {self.size} m²")
        if self.trip is not None:
            components.append(f"Rejsetid: {self.trip.duration:.0f} min")
        if self.energy_label is not None:
            components.append(f"Energimærke: {self.energy_label}")
        if self.year is not None:
            components.append(f"Bygget: {self.year}")
        if self.time_on_market is not None:
            components.append(f"Liggetid: {self.time_on_market} dage")
        if self.monthly_fee is not None:
            components.append(
                f"Mdl. ejerudgifter: {dk_format(self.monthly_fee)} kr./md"
            )
        if self.noise is not None:
            components.append(f"Støj: {self.noise.dB_min} - {self.noise.dB_max} dB")
        if self.school is not None:
            components.append(
                f"Skole: {self.school.name} ({self.school_travel_time.distance_text})"
                if self.school_travel_time
                else ""
            )
        if self.title is not None:
            components.append(f"Titel: {self.title}")
            # components.append(
            #     "Title:\n"
            #     + textwrap.indent(textwrap.fill(self.title, width=40), "    ")
            # )
        return components

    def to_html(self) -> str:
        """Get the home as an HTML string.

        Returns:
            The home as an HTML string.
        """
        components = [f"<a href='{self.case_url}'>{self.address}</a>"]
        components += self._get_components()

        return "\n".join(components)

    def to_text(self) -> str:
        """Get the home as a text string.

        Returns:
            The home as a text string.
        """
        components = [f"URL: {self.case_url}", f"Addresse: {self.address}"]
        components += self._get_components()
        return "\n".join(components)

    @retry(max_retries=5)
    def extend_with_gis(
        self,
        municipalities: list[str],
        gis_dir: Path,
        destId: str = "8600646",  # (Nørreport st)
        originBike: str = "1,0,20000",
        date: str = "2025-07-28",
        time: str = "08:00",
    ) -> None:
        """Extend the home with GIS data."""
        if self.coordinates is None:
            origin_location = rejseplanen.Location.from_string(self.address)
        else:
            origin_location = rejseplanen.Location(
                lat=self.coordinates.lat,
                lon=self.coordinates.lon,
            )

        trip_request = rejseplanen.TripRequest(
            originCoordLat=origin_location.lat,
            originCoordLong=origin_location.lon,
            destId=destId,  # (Nørreport st)
            originBike=originBike,
            # destCoordLat="55.683597",  # Destination latitude
            # destCoordLong="12.5708992",  # Destination longitude
            date=date,  # Monday's date in YYYY-MM-DD format
            time=time,  # Time in hh:mm format
        )
        trip_response = trip_request.get_response()

        journey = rejseplanen.Journey(**trip_response)
        trip = journey.get_fastest_trip()

        gis_noise = get_gis_noise(gis_dir)
        noise = gis_noise.get_noise(lat=origin_location.lat, lon=origin_location.lon)

        gis_schools = get_gis_schools(
            gis_dir=gis_dir,
            municipalities=tuple(municipalities),
        )
        school = gis_schools.get_school(
            lat=origin_location.lat, lon=origin_location.lon
        )

        travel_time = get_bike_time(
            origin=f"{origin_location.lat}, {origin_location.lon}",
            destination=f"{school.name}, {school.municipality}",
        )

        self.origin_location = origin_location
        self.journey = journey
        self.trip = trip
        self.noise = noise
        self.school = school
        self.school_travel_time = travel_time

    def flatten(self) -> FlatHome:
        """Flatten the home data.

        This method returns a FlatHome object with all the data from the home
        """
        parameters = self.model_dump()

        if self.coordinates is not None:
            parameters["coord_lat"] = self.coordinates.lat
            parameters["coord_lon"] = self.coordinates.lon

        if self.trip is not None:
            parameters["trip_duration"] = self.trip.duration
            parameters["trip_changes"] = self.trip.mode_changes
            parameters["trip_methods"] = self.trip.methods_as_string
            parameters["trip_description"] = self.trip.description

        if self.noise is not None:
            parameters["noise_dB_min"] = self.noise.dB_min
            parameters["noise_dB_max"] = self.noise.dB_max

        if self.school is not None:
            parameters["school_name"] = self.school.name
        if self.school_travel_time is not None:
            parameters["school_bike_distance"] = self.school_travel_time.distance
            parameters["school_bike_duration"] = self.school_travel_time.duration

        return FlatHome(**parameters)

    def export(self) -> dict:
        """Export the home data to a csv-ready dict.

        First it flattens the data, then it dumps it to a dict.
        """
        return self.flatten().model_dump(mode="json")
