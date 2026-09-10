"""Split an Amazon search page into featured (sponsored) and organic results.

Verified against the live ScrapingBee Amazon API on 2026-09-10.
Set SCRAPINGBEE_API_KEY in your environment before running.
"""

import os

import requests

BASE = "https://app.scrapingbee.com/api/v1"
KEY = os.environ["SCRAPINGBEE_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}"}


def search(query, pages=1, **params):
    """Amazon search results. 5 credits per page on a light request."""
    r = requests.get(
        f"{BASE}/amazon/search",
        headers=HEADERS,
        params={"query": query, "pages": pages, **params},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def product(asin, **params):
    """Structured product detail. Takes 'query', not 'asin'."""
    r = requests.get(
        f"{BASE}/amazon/product",
        headers=HEADERS,
        params={"query": asin, **params},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def pricing(asin, **params):
    """Seller offers. This endpoint takes 'asin', not 'query'."""
    r = requests.get(
        f"{BASE}/amazon/pricing",
        headers=HEADERS,
        params={"asin": asin, **params},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    page = search("fitness tracker", sort_by="featured")
    products = page["products"]

    featured = [p for p in products if p["is_sponsored"]]
    organic = [p for p in products if not p["is_sponsored"]]

    print(f"{page['products_count']} products, {len(featured)} featured, {len(organic)} organic")

    for p in featured:
        print(f"  ad  slot {p['sponsored_position']}  {p['price']} {p['currency']}  {p['title'][:60]}")

    for p in organic[:5]:
        badge = "choice" if p["is_amazons_choice"] else ("bestseller" if p["best_seller"] else "")
        print(f"  org rank {p['organic_position']}  {p['price']} {p['currency']}  {badge}  {p['title'][:50]}")

    if organic:
        asin = organic[0]["asin"]
        detail = product(asin)
        print(f"\n{detail['brand']} / {detail['price']} {detail['currency']} / {detail['rating']} stars")
        for offer in pricing(asin)["pricing"]:
            print(f"  offer {offer['seller']}  {offer['price']}  {offer['condition']}")
