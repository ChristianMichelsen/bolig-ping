"""Main script to scrape and update the database with new homes from Boligsiden."""

# %%

import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from rich import print
from tinydb import TinyDB, where
from tqdm.auto import tqdm

from bolig_ping.data_models import AddressType, FlatHome, SearchQuery

# %%

MUNICIPALITIES = [
    "Lyngby-Taarbæk",  # Lyngby / Virum
    "Rudersdal",  # Holte
    "Furesø",  # Farum
    "Gladsaxe",  # Bagsværd
    "Gentofte",  # Gentofte
]

GIS_DIR = Path("data") / "gis"

ADDRESS_TYPE: list[AddressType] = [
    "villa",
    "rækkehus",
    "villalejlighed",
]

MAX_TRIP_DURATION = 40

# %%

db = TinyDB("data/db.json")

# %%

query = SearchQuery(
    address_type=ADDRESS_TYPE,
    min_price=7_500_000,
    # min_price=10_500_000,
    max_price=10_700_000,
    min_size=110,
    max_size=250,
    min_rooms=3,
    max_rooms=8,
    municipality=MUNICIPALITIES,
    # energy_label=["A", "B"],
    # polygon = "12.467721,55.768600|12.482656,55.759274|12.506124,55.758190|12.519962,55.767550|12.510944,55.778394|12.509179,55.788153|12.506264,55.797984|12.481980,55.806335|12.474718,55.817548|12.453262,55.816325|12.433050,55.812394|12.429428,55.811859|12.423876,55.811171|12.415170,55.800073|12.423254,55.788798|12.427297,55.776908|12.446732,55.771573|12.467721,55.768600"  # noqa: E501
)

homes = query.get_homes()

if homes is None:
    raise ValueError("No homes found.")


home = homes[0]
print(f"Found a total of {len(homes)} homes from Boligsiden.")

# %%

today = datetime.date.today()

i_update = 0
i_new = 0
i_new_price = 0

new_prices: list[FlatHome] = []
new_homes: list[FlatHome] = []

print("Comparing the homes to the existing database...")
for home in tqdm(homes):
    query = where("case_url") == home.case_url

    # Check if the home is already in the database
    if db.count(query) > 1:
        raise ValueError("Duplicate entry in database.")

    elif db.count(query) == 1:
        old_price = db.search(query)[0]["price"]
        new_price = home.price
        if old_price != new_price:
            new_prices.append(home.flatten())
            print(f"Price change detected: {old_price} -> {new_price}")

        d_update = {
            "last_updated": str(today),
            "price": new_price,
            "time_on_market": home.time_on_market,
            "price_change_percentage": home.price_change_percentage,
            "raw_json": home.raw_json,
        }
        db.update(d_update, query)
        i_update += 1

    else:
        # home.address
        home.extend_with_gis(
            municipalities=MUNICIPALITIES,
            gis_dir=GIS_DIR,
            date="2025-07-28",
        )
        flat_home = home.flatten()
        flat_home_json = flat_home.model_dump(mode="json")
        flat_home_json["day_added"] = str(today)
        db.insert(flat_home_json)
        new_homes.append(flat_home)
        i_new += 1

# Find homes that are still for sale by checking if the last updated date is today
query_still_for_sale = where("last_updated") == str(today)
db.update({"still_for_sale": True}, query_still_for_sale)
db.update({"still_for_sale": False}, ~query_still_for_sale)

# %%

query_still_for_sale = where("still_for_sale") == True  # noqa: E712
N_still_for_sale = db.count(query_still_for_sale)  # noqa: E712
N_not_for_sale = db.count(~query_still_for_sale)  # noqa: E712

print(f"Added {i_new} new home(s)")
print(f"Updated {i_update} homes ({len(new_prices)} new prices)")
print(f"Number of homes still for sale: {N_still_for_sale}")
print(f"Number of homes not for sale anymore: {N_not_for_sale}")

# %%

print("New homes:")
for home in new_homes:
    print(home.to_text())

# %%

print("New prices:")
for home in new_prices:
    print(home.to_text())

# %%


query_trip_duration = where("trip_duration") < MAX_TRIP_DURATION
query_good_homes = query_still_for_sale & query_trip_duration
df = pd.DataFrame(db.search(query_good_homes))


for address_type, group in df.groupby("address_type"):
    if address_type == "villa":
        break

group = group.sort_values("trip_duration")

for i, (_, row) in enumerate(group.iterrows()):
    flat_home = FlatHome(**row.replace({np.nan: None}))
    print(flat_home.to_text())
    print("")

    if i > 10:
        break

# %%
