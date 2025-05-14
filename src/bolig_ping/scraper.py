"""Scraping homes available satisfying the given criteria."""

import json
import logging

import requests
from tqdm.auto import tqdm

from .data_models import Home, SearchQuery

logger = logging.getLogger(__package__)


def scrape_results(search_query: SearchQuery) -> list[Home] | None:
    """Scrape the results of a home search query.

    Args:
        search_query:
            The search query to scrape results for.

    Returns:
        A list of homes that satisfy the search query, or None if no results were found.

    Raises:
        HTTPError:
            If there was an error in the HTTP request.
    """
    logger.info("Fetching results...")

    # Get the results from the search query
    query_url = search_query.get_url()
    logger.info(f"Fetching results from {query_url}")
    response = requests.get(url=query_url)
    response.raise_for_status()

    # Parse the response
    result_dict = json.loads(response.text)
    results = result_dict["cases"]
    if results is None:
        return None

    # Get the number of pages
    num_results = result_dict["totalHits"]
    num_pages = num_results // len(results)
    if num_results % len(results) != 0:
        num_pages += 1

    # Get the first page of results
    homes = [Home.from_nested_dict(result) for result in results]

    # Scrape the remaining pages
    if num_pages > 1:
        with tqdm(desc="Scraping homes from boligsiden.dk", total=num_results) as pbar:
            pbar.update(len(homes))
            for page_idx in range(2, num_pages + 1):
                url = search_query.get_url(page=page_idx)
                response = requests.get(url=url)
                response.raise_for_status()
                result_dict = json.loads(response.text)
                results = result_dict["cases"]
                new_homes = [Home.from_nested_dict(result) for result in results]
                homes.extend(new_homes)
                homes = list(set(homes))
                pbar.update(len(new_homes))

        # Ensure that the progress bar is at 100% at the end
        pbar.n = pbar.total

    return homes
