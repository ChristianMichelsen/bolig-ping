# %%

from pathlib import Path

from rich import print

from bolig_ping.data_models import SearchQuery

# %%

MUNICIPALITIES = [
    "Lyngby-Taarbæk",  # Lyngby / Virum
    "Rudersdal",  # Holte
    "Furesø",  # Farum
    "Gladsaxe",  # Bagsværd
    "Gentofte",  # Gentofte
]

GIS_DIR = Path("data") / "gis"


# %%

query = SearchQuery(
    address_type=[
        "villa",
        "rækkehus",
        "villalejlighed",
    ],
    # min_price=7_500_000,
    min_price=10_500_000,
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
print(home)

# %%

home.case_id
home.case_url

home.to_html()
print(home.to_text())


# %%

home.extend_with_gis(municipalities=MUNICIPALITIES, gis_dir=GIS_DIR)
print(home.to_text())


# %%
