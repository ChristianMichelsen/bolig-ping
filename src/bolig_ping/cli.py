"""Command line interface for the project."""

import logging

import cyclopts
from dotenv import load_dotenv

from .data_models import SearchQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s ⋅ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__package__)

load_dotenv(dotenv_path=".env")


app = cyclopts.App()


@app.default()
def run(search_query: SearchQuery) -> None:
    """Run the CLI with the given search query."""
    print(search_query)


if __name__ == "__main__":
    #     main()
    app()
