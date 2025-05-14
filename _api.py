from pathlib import Path
from typing import Annotated

import cyclopts.config
from cyclopts import App, Parameter
from rich import print

from src.bolig_ping.data_models import SearchQuery

app = App(
    # default_parameter=Parameter(consume_multiple=True),
)


def validate_search_query(_: str, value: str | None) -> None:
    if value is None:
        raise AssertionError("You must provide a search query.")


@app.default
def default(
    search_query: Annotated[
        SearchQuery | None, Parameter(name="*", validator=validate_search_query)
    ] = None,
) -> None:
    assert search_query is not None, "You must provide a search query."

    print("Running with the following search query:")
    print(search_query.export_to_dict())


@app.meta.default
def load_config(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    config: Path | None = None,
) -> None:
    if config is not None:
        app.config = cyclopts.config.Toml(config)
    app(tokens)


if __name__ == "__main__":
    app.meta()
