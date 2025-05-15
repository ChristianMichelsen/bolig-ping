"""Data models used in the project."""

import datetime
import logging
import textwrap
from typing import Literal, Self

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, computed_field, field_serializer, field_validator

# %%

logger = logging.getLogger(__package__)

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


ENERGY_LABELS = Literal["A", "B", "C", "D", "E", "F", "G"]


# %%


class SearchQuery(BaseModel):
    """A search query for the Boligsiden API."""

    # Boligtype
    address_type: list[AddressType] | None = Field(
        default=None,
        serialization_alias="addressTypes",
    )
    # Kommune
    municipality: list[str] | None = Field(
        default=None,
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


class Home(BaseModel):
    """A search result from the Boligsiden API."""

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
    per_area_price: float | None = Field(ge=0)
    coordinates: Coordinates | None
    address_type: AddressType | None
    basement_area: int | None = Field(ge=0)
    case_id: str
    case_url: str
    title: str
    lot_area: int = Field(ge=0)
    weighted_area: float | None = Field(ge=0)
    image: SearchImage | None
    price_change_percentage: float | None = None
    last_updated: datetime.date

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
            per_area_price=result.get("perAreaPrice"),
            coordinates=Coordinates(
                lat=result["coordinates"]["lat"],
                lon=result["coordinates"]["lon"],
            ),
            address_type=result.get("addressType"),
            basement_area=result.get("basementArea"),
            case_id=result["caseID"],
            case_url=result["caseUrl"],
            title=result["descriptionTitle"],
            lot_area=result["lotArea"],
            weighted_area=result.get("weightedArea"),
            image=sorted(
                result["defaultImage"]["imageSources"],
                key=lambda img: img["size"]["height"],
                reverse=True,
            )[0],
            price_change_percentage=result.get("priceChangePercentage"),
            last_updated=datetime.date.today(),
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
        components.append(f"Price: {self.price:,} kr.")
        if self.num_rooms is not None:
            components.append(
                f"Number of rooms: {self.num_rooms}"
                f" ({self.bathrooms} bathrooms, {self.toilets} toilets)"
            )
        if self.size is not None:
            components.append(f"Size: {self.size} m²")
        if self.monthly_fee is not None:
            components.append(f"Monthly fee: {self.monthly_fee:,} kr./md")
        if self.energy_label is not None:
            components.append(f"Energy label: {self.energy_label}")
        if self.year is not None:
            components.append(f"Year built: {self.year}")
        if self.time_on_market is not None:
            components.append(f"Time on market: {self.time_on_market} days")
        if self.title is not None:
            components.append(
                "Title:\n"
                + textwrap.indent(textwrap.fill(self.title, width=40), "    ")
            )
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
        components = [f"URL: {self.case_url}", f"Address: {self.address}"]
        components += self._get_components()
        return "\n".join(components)


# %%
