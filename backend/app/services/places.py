"""
Google Places lookup for the chatbot's "find cheaper places near me" tool.

Uses Places API (New) Text Search — a single free-text query (e.g. "cheap tacos
near Austin TX") is enough, no separate geocoding step required.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel,places.currentOpeningHours.openNow"

# Places API (New) reports price as an enum rather than 0-4 like the legacy API.
PRICE_LEVEL_ORDER = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}
PRICE_LEVEL_LABELS = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}


def search_places(query: str, location: str, max_results: int = 5) -> dict:
    """
    Searches Google Places for `query` near `location`, sorted cheapest-first
    (unknown price level sorts last, then by rating). Returns a dict with either
    a `results` list or an `error` string — never raises, so the chatbot tool
    loop always has something safe to relay to the user.
    """
    if not settings.google_places_api_key:
        return {"error": "Places search isn't configured on this server."}

    try:
        resp = httpx.post(
            TEXT_SEARCH_URL,
            json={"textQuery": f"{query} near {location}"},
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.google_places_api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            timeout=10.0,
        )
        data = resp.json()
        if resp.status_code != 200:
            logger.error("Google Places returned %s for query=%r: %s", resp.status_code, query, data)
            return {"error": "Places search failed."}
    except httpx.HTTPError:
        logger.exception("Google Places request failed for query=%r location=%r", query, location)
        return {"error": "Couldn't reach Google Places right now."}

    places = []
    for r in data.get("places", []):
        price_level = r.get("priceLevel")
        places.append(
            {
                "name": (r.get("displayName") or {}).get("text"),
                "address": r.get("formattedAddress"),
                "rating": r.get("rating"),
                "num_ratings": r.get("userRatingCount"),
                "price": PRICE_LEVEL_LABELS.get(price_level, "Unknown"),
                "open_now": (r.get("currentOpeningHours") or {}).get("openNow"),
                "_price_order": PRICE_LEVEL_ORDER.get(price_level),
            }
        )

    places.sort(key=lambda p: (p["_price_order"] is None, p["_price_order"] or 0, -(p["rating"] or 0)))
    for p in places:
        del p["_price_order"]
    return {"results": places[:max_results]}
