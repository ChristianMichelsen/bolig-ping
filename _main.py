# %%

import datetime
from pathlib import Path

from rich import print
from tinydb import TinyDB, where
from tqdm.auto import tqdm

from bolig_ping.data_models import AddressType, SearchQuery

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

new_prices = []
new_homes = []

for home in tqdm(homes):
    query = where("case_url") == home.case_url

    # Check if the home is already in the database
    if db.count(query) > 1:
        raise ValueError("Duplicate entry in database.")

    elif db.count(query) == 1:
        old_price = db.search(query)[0]["price"]
        new_price = home.price
        if old_price != new_price:
            new_prices.append(home)
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
        home.extend_with_gis(municipalities=MUNICIPALITIES, gis_dir=GIS_DIR)
        flat_home = home.export()
        flat_home["day_added"] = str(today)
        db.insert(flat_home)
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

query_trip_duration = where("trip_duration") < MAX_TRIP_DURATION
query_good_houses = query_still_for_sale & query_trip_duration
good_homes = db.search(query_good_houses)
len(good_homes)
