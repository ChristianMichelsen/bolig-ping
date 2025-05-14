# %%

from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from pyogrio.errors import DataSourceError
from shapely.geometry import Point
from tqdm.auto import tqdm

# %%

try:
    gdf = gpd.read_file("output.fgb")

except DataSourceError:
    """https://mst.dk/erhverv/tilskud-miljoeviden-og-data/data-og-databaser/miljoegis-data-om-natur-og-miljoe-paa-webkort/hent-data-udstillet-paa-miljoegis"""

    GIS_DIR = Path("data") / "gis" / "2022_noise_shp"
    shapefile_paths = list(GIS_DIR.rglob("*.shp"))

    gdfs = []
    for shapefile_path in tqdm(shapefile_paths):
        # break
        # Load the shapefile
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
    gdf = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True).assign(
            source=lambda x: x.source.astype("category")
        )
    )

# %%

# Display the first few rows of the GeoDataFrame
gdf
gdf.shape
gdf.iloc[0]
gdf.iloc[1:2].plot()

gdf.info()

gdf.crs


# Define the point you want to check
point = Point(12.592811, 55.669127)  # test i voldgraven
point = Point(12.5910639, 55.6698456)  # Sofiegade 24
point = Point(12.4721217, 55.7955233)  # Virum station
# point = Point(12.5582424, 55.6652013)  # Dybbølsbro

point_gs = gpd.GeoSeries([point], crs=gdf.crs.to_string())

# Find rows where the geometry contains the point
rows_containing_point = gdf[gdf.geometry.contains(point)]
rows_containing_point

gdf.loc[rows_containing_point.index].plot()


gdf[gdf.source == "dk_2022_jernbane_1_5m.shp"].plot()


# %%


# gdf.to_file("output.fgb", driver="FlatGeobuf")


# %%


most_eastern_points = gdf.geometry.apply(lambda geom: geom.bounds[2])
most_northern_points = gdf.geometry.apply(lambda geom: geom.bounds[3])

Ballerup = 55.7608253, 12.357504

mask_east_of_Ballerup = most_eastern_points > Ballerup[1]
mask_north_of_Ballerup = most_northern_points > Ballerup[0]


gdf_filtered = gdf[mask_east_of_Ballerup & mask_north_of_Ballerup]
gdf_filtered.plot()


# Find rows where the geometry contains the point
rows_containing_point = gdf_filtered[gdf_filtered.geometry.contains(point)]
rows_containing_point

gdf_filtered.loc[rows_containing_point.index].plot()

gdf_filtered.to_file("output_filtered.fgb", driver="FlatGeobuf")


gdf_filtered.source.value_counts()


# # #%%

# from shapely.geometry import Polygon

# # Define the bounding box of your region (min_lon, min_lat, max_lon, max_lat)
# region_bounds = (
#     12.42,
#     55.75,
#     12.53,
#     55.83,
# )  # Example: bounding box for a region in the USA

# # Create a Polygon for the region
# region_polygon = Polygon(
#     [
#         (region_bounds[0], region_bounds[1]),  # Bottom-left
#         (region_bounds[0], region_bounds[3]),  # Top-left
#         (region_bounds[2], region_bounds[3]),  # Top-right
#         (region_bounds[2], region_bounds[1]),  # Bottom-right
#         (region_bounds[0], region_bounds[1]),  # Close the polygon
#     ]
# )

# # Convert the region polygon to a GeoDataFrame
# region_gdf = gpd.GeoDataFrame([1], geometry=[region_polygon], crs=gdf_filtered.crs)
# region_gdf.plot()

# # Clip the roads GeoDataFrame to the region
# gdf.iloc[47604 : 47604 + 1].plot()
# clipped_gdf = gpd.clip(gdf.iloc[47604 : 47604 + 1], region_gdf)
# # clipped_gdf = gpd.clip(gdf_filtered, region_gdf)

# # Save or inspect the clipped GeoDataFrame
# clipped_gdf.plot()


# %%


# Reproject to Web Mercator (EPSG:3857) for compatibility with basemaps
clipped_gdf = gdf.iloc[47604 : 47604 + 1]

# Plot the clipped GeoDataFrame
fig, ax = plt.subplots(figsize=(10, 10))
clipped_gdf.to_crs(epsg=3857).plot(ax=ax, color="blue", linewidth=0.5, alpha=0.7)


# Plot the point
point_gs.to_crs(epsg=3857).plot(
    ax=ax, color="red", marker="o", markersize=50, label="Point of Interest"
)


# Add a basemap using contextily
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager)

# Set plot title and remove axes for a cleaner map
ax.set_title("Roads within the Specified Region", fontsize=16)
ax.axis("off")

# Show the plot
plt.show()
# %%
