"""Load GIS noise data."""

from pathlib import Path
from typing import Self

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel
from shapely.geometry import Point
from tqdm.auto import tqdm

# %%


def get_gis_noise_all_data(path: str | Path) -> gpd.GeoDataFrame:
    """Load all GIS noise data from the specified directory.

    https://mst.dk/erhverv/tilskud-miljoeviden-og-data/data-og-databaser/miljoegis-data-om-natur-og-miljoe-paa-webkort/hent-data-udstillet-paa-miljoegis
    """
    output_file_all = Path("data") / "gis" / "noise_all.fgb"

    if output_file_all.exists():
        print(f"Loading {output_file_all} from cache")
        gdf_all = gpd.read_file(output_file_all)
        return gdf_all

    print(f"Loading GIS noise data from {path}, please wait...")

    shapefile_paths = list(Path(path).rglob("*.shp"))

    gdfs = []
    for shapefile_path in tqdm(shapefile_paths):
        gdf = gpd.read_file(shapefile_path)

        if "iso1" in gdf.columns:
            gdf = gdf.rename(columns={"iso1": "dB_min", "iso2": "dB_max"})

        try:
            gdf = (
                gdf.to_crs("EPSG:4326")  # WGS84
                .rename(columns={"isov1": "dB_min", "isov2": "dB_max"})
                .loc[:, ["dB_min", "dB_max", "geometry"]]
                .assign(source=shapefile_path.stem)
            )
            gdfs.append(gdf)
        except KeyError:
            print(f"KeyError: {shapefile_path}")
            print(gdf.columns)
            print()
            continue

    # Concatenate all GeoDataFrames into one and convert source to categorical
    gdf_all = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True).assign(
            source=lambda x: x.source.astype("category")
        )
    )
    gdf_all.to_file(output_file_all, driver="FlatGeobuf")

    return gdf_all


# %%


def filter_gis_noise_data_all(gdf_all: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter the GIS noise data to only include relevant areas."""
    most_western_points = gdf_all.geometry.apply(lambda geom: geom.bounds[0])
    most_southern_points = gdf_all.geometry.apply(lambda geom: geom.bounds[1])
    most_eastern_points = gdf_all.geometry.apply(lambda geom: geom.bounds[2])
    most_northern_points = gdf_all.geometry.apply(lambda geom: geom.bounds[3])

    SouthWestCorner = 55.7608253, 12.357504  # around Ballerup
    NorthEastCorner = 55.885954, 12.627216  # Between Rungsted and Ven

    mask_north_of_Ballerup = most_northern_points > SouthWestCorner[0]
    mask_east_of_Ballerup = most_eastern_points > SouthWestCorner[1]

    mask_south_of_Rungsted = most_southern_points < NorthEastCorner[0]
    mask_west_of_Rungsted = most_western_points < NorthEastCorner[1]

    mask_combined = (
        mask_north_of_Ballerup
        & mask_east_of_Ballerup
        & mask_south_of_Rungsted
        & mask_west_of_Rungsted
    )

    gdf = gdf_all[mask_combined]
    # gdf.plot()
    return gdf


def get_gis_noise_data(path: str | Path) -> gpd.GeoDataFrame:
    """Load GIS noise data from the specified directory.

    https://mst.dk/erhverv/tilskud-miljoeviden-og-data/data-og-databaser/miljoegis-data-om-natur-og-miljoe-paa-webkort/hent-data-udstillet-paa-miljoegis
    """
    output_file = Path("data") / "gis" / "noise.fgb"
    output_file_all = Path("data") / "gis" / "noise_all.fgb"

    if output_file.exists():
        print(f"Loading {output_file} from cache")
        gdf = gpd.read_file(output_file_all)
        return gdf

    gdf_all = get_gis_noise_all_data(path)
    print("Filtering GIS noise data, please wait...")
    gdf = filter_gis_noise_data_all(gdf_all)

    gdf.to_file(output_file, driver="FlatGeobuf")

    return gdf


# %%


class Noise(BaseModel):
    """Noise data."""

    rows: gpd.GeoDataFrame | None

    dB_min: float | None
    dB_max: float | None


class GisNoise(BaseModel, arbitrary_types_allowed=True):
    """GIS noise data."""

    gdf: gpd.GeoDataFrame

    @classmethod
    def from_dir(
        cls,
        path: str | Path,
    ) -> Self:
        """Load GIS noise data from the specified directory.

        https://mst.dk/erhverv/tilskud-miljoeviden-og-data/data-og-databaser/miljoegis-data-om-natur-og-miljoe-paa-webkort/hent-data-udstillet-paa-miljoegis
        """
        gdf = get_gis_noise_data(path)
        return cls(gdf=gdf)

    def get_noise(self, lon: float, lat: float) -> Noise:
        """Get noise data for a specific point."""
        # Create a GeoSeries for the point
        # point_gs = gpd.GeoSeries([point], crs=self.gdf.crs.to_string())

        point = Point(lon, lat)

        # Find rows where the geometry contains the point
        rows = self.gdf[self.gdf.geometry.contains(point)]

        if len(rows) == 0:
            return Noise(
                rows=rows,
                dB_min=None,
                dB_max=None,
            )

        dB_max = rows["dB_max"].max()
        dB_min = rows["dB_min"].min()

        noise = Noise(
            rows=rows,
            dB_min=dB_min,
            dB_max=dB_max,
        )
        return noise
