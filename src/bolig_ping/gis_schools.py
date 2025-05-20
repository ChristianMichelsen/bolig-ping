# %%

"""https://fkg-kort.mapcentia.com/app/fkg/fkg/#osm/12/12.3799/55.8159/fkg.t_5710_born_skole_dis."""

from pathlib import Path
from typing import Self

import geopandas as gpd
import requests
from pydantic import BaseModel, Field
from shapely.geometry import Point

# %%

GIS_DIR = Path("data") / "gis"


# %%


def get_school_disctricts_as_geojson() -> dict:
    """Get school districts as GeoJSON."""
    url = "https://fkg-kort.mapcentia.com/api/sql/fkg"
    headers = {
        "Referer": "https://fkg-kort.mapcentia.com/app/fkg/fkg/",
        "User-Agent": "python-requests/2.x",
        "Content-Type": "application/x-www-form-urlencoded; charseselectt=UTF-8",
    }
    data = {
        "geoformat": "wkt",
        "format": "geojson",
        "client_encoding": "UTF8",
        "srs": "4326",
        "q": "SELECT * FROM fkg.t_5710_born_skole_dis",
    }

    response = requests.post(url, headers=headers, data=data)
    geojson = response.json()

    if not geojson.get("type") == "FeatureCollection":
        raise ValueError("Response is not a valid GeoJSON.")

    return geojson


def get_gis_schools_all_data(output_file_all: Path) -> gpd.GeoDataFrame:
    """Get all GIS school data."""
    if output_file_all.exists():
        print(f"Loading {output_file_all} from cache")
        gdf_all = gpd.read_file(output_file_all)
        return gdf_all

    print("Downloading GIS school data, please wait...")
    geojson = get_school_disctricts_as_geojson()
    gdf_all = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")
    gdf_all.to_file(output_file_all, driver="GeoJSON", index=False)

    return gdf_all


# %%


def get_gis_school_data(
    gis_dir: str | Path,
    municipalities: list[str],
) -> gpd.GeoDataFrame:
    """Get GIS school data for the specified municipalities."""
    municipalities = sorted(municipalities)
    output_file_all = Path(gis_dir) / "schools_all.geojson"
    output_file = Path(gis_dir) / ("schools_" + "_".join(municipalities) + ".geojson")

    if output_file.exists():
        # print(f"Loading {output_file} from file")
        gdf = gpd.read_file(output_file)
        return gdf

    municipalities = [s + " Kommune" for s in municipalities if "Kommune" not in s]

    gdf_all = get_gis_schools_all_data(output_file_all)
    gdf = gdf_all.query(f"cvr_navn in {municipalities}")
    gdf.to_file(output_file, driver="GeoJSON", index=False)

    return gdf


# %%


class School(BaseModel, arbitrary_types_allowed=True):
    """Noise data."""

    rows: gpd.GeoDataFrame | None = Field(repr=False)

    name: str | None
    start_grade: str | None
    end_grade: str | None
    municipality: str | None


class GisSchools(BaseModel, arbitrary_types_allowed=True):
    """GIS school data."""

    gdf: gpd.GeoDataFrame

    @classmethod
    def from_dir(cls, gis_dir: str | Path, municipalities: list[str]) -> Self:
        """Load GIS school data from the specified directory."""
        gdf = get_gis_school_data(gis_dir, municipalities)
        return cls(gdf=gdf)

    def get_school(self, lon: float, lat: float) -> School:
        """Get school data for a specific point."""
        gdf = self.gdf

        point = Point(lon, lat)

        rows = gdf[gdf.geometry.contains(point)].query("starttrin == '0. klasse'")
        rows

        if len(rows) == 0:
            return School(
                rows=rows,
                name=None,
                start_grade=None,
                end_grade=None,
                municipality=None,
            )

        return School(
            rows=rows,
            name=rows.iloc[0]["udd_distrikt_navn"],
            start_grade=rows.iloc[0]["starttrin"],
            end_grade=rows.iloc[0]["slutttrin"],
            municipality=rows.iloc[0]["cvr_navn"],
        )
