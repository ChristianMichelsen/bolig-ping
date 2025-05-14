# %%

"""https://fkg-kort.mapcentia.com/app/fkg/fkg/#osm/12/12.3799/55.8159/fkg.t_5710_born_skole_dis."""

from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

# %%

path = Path("data") / "gis" / "skole" / "file.geojson"


gdf = gpd.read_file(path)


# %%


point = Point(12.5910639, 55.6698456)  # Sofiegade 24
point = Point(12.4721217, 55.7955233)  # Virum station
point = Point(12.5582424, 55.6652013)  # Dybbølsbro
point = Point(12.445640186205083, 55.79231084902392)  # Frederiksdal
# point = Point(12.47410512937563, 55.813535108812154)  # Holte


# Create a GeoSeries for the point
point_gs = gpd.GeoSeries([point], crs=gdf.crs.to_string())

rows_containing_point = gdf[gdf.geometry.contains(point)].query(
    "starttrin == '0. klasse'"
)
rows_containing_point

if len(rows_containing_point) == 0:
    raise ValueError("No rows contain the point.")
elif len(rows_containing_point) > 1:
    raise ValueError("Multiple rows contain the point. Please refine your search.")
else:
    name = rows_containing_point["udd_distrikt_navn"].iloc[0]


# %%


# Plot the clipped GeoDataFrame
fig, ax = plt.subplots(figsize=(10, 10))

gdf.loc[rows_containing_point.index].to_crs(epsg=3857).plot(
    ax=ax, color="blue", linewidth=0.5, alpha=0.2
)


# Plot the point
point_gs.to_crs(epsg=3857).plot(
    ax=ax, color="red", marker="o", markersize=50, label="Point of Interest"
)

# Add a basemap using contextily
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager)

# Set plot title and remove axes for a cleaner map
ax.set_title(f"Skoledistrikt: {name}", fontsize=16)
ax.axis("off")

# Show the plot
plt.show()

# %%
