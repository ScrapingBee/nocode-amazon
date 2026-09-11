# No Code Amazon Scraper

<p align="center">
  <a href="https://www.scrapingbee.com/">
    <img src="https://github.com/user-attachments/assets/e6938ee5-91d4-4040-947c-016e1457e4c0" alt="nocode-amazon" />
  </a>
</p>

[![checks](https://github.com/ScrapingBee/nocode-amazon/workflows/checks/badge.svg)](https://github.com/ScrapingBee/nocode-amazon/actions)
[![pypi](https://img.shields.io/pypi/v/nocode-amazon.svg)](https://pypi.org/project/nocode-amazon/)
[![python](https://img.shields.io/pypi/pyversions/nocode-amazon.svg)](https://pypi.org/project/nocode-amazon/)
[![npm](https://img.shields.io/npm/v/nocode-amazon.svg)](https://www.npmjs.com/package/nocode-amazon)
[![node](https://img.shields.io/node/v/nocode-amazon.svg)](https://www.npmjs.com/package/nocode-amazon)
[![license](https://img.shields.io/github/license/ScrapingBee/nocode-amazon.svg)](LICENSE)

Two ways to pull Amazon product data, in the order most people actually need them. Lane one is a [no code Amazon scraper](https://www.scrapingbee.com/blog/nocode-amazon/) built from Make and Airtable, with no repository to clone and nothing to deploy. Lane two is the dedicated Amazon endpoints on [ScrapingBee's web scraping API](https://www.scrapingbee.com/features/ai-web-scraping-api/), for the point where a spreadsheet stops being enough.

Both lanes read the same public Amazon pages. The difference is who runs the loop.

Everything below was executed against the live API on 2026-09-10. Every response field, every parameter name and every credit figure in this README came back from a real call, not from a documentation page.

## Lane one: the spreadsheet route

The no code lane is five moving parts and no code at all:

1. A Make scenario, triggered on a schedule.
2. A ScrapingBee module inside it, set to **Make an API call**, method `GET`.
3. An Amazon search URL in the URL field.
4. Extraction rules, pasted into **Extract Rules (JSON)** under **Show advanced settings**.
5. An Iterator, then an Airtable **Create a Record** action, so one scraped product becomes one row.

The extraction rules are the only part that looks like programming, and they are just a description of the page:

```json
{
  "results": {
    "selector": "div.s-result-item.s-asin",
    "type": "list",
    "output": {
      "link": { "selector": "a.a-link-normal", "output": "@href" },
      "name": "span.a-size-medium.a-color-base.a-text-normal",
      "price": "span.a-offscreen"
    }
  }
}
```

Leave **Render JS** off. Amazon search results are in the delivered HTML and rendering costs extra credits for nothing. In the Airtable step, `parseNumber(price; ".")` strips the currency symbol, and the `link` values are relative, so prefix `https://www.amazon.com` before writing the row.

The [Make integration](https://www.scrapingbee.com/features/make/) is the version documented here. [n8n](https://www.scrapingbee.com/features/n8n/) and [Zapier](https://www.scrapingbee.com/features/zapier/) expose the same call if your automation already lives somewhere else.

### Where lane one runs out

The spreadsheet route breaks on three things, and they arrive in this order:

- **Selectors rot.** `span.a-size-medium.a-color-base.a-text-normal` is an Amazon build detail. When it changes, your scenario silently writes empty names.
- **You cannot tell a paid placement from an earned one.** Every card in `div.s-result-item.s-asin` looks identical to a CSS selector, so a sponsored slot and a rank 3 organic result land in the same Airtable column.
- **One page is 23 products.** Pagination in a visual scenario means duplicating modules.

Lane two fixes all three, because ScrapingBee parses Amazon server side and hands back the labels.

## Lane two: the dedicated Amazon endpoints

Three endpoints, no selectors, no HTML:

| Endpoint | Required parameter | Returns |
|---|---|---|
| `/api/v1/amazon/search` | `query` | `products`, `products_count`, `refinements`, `url`, `page` |
| `/api/v1/amazon/product` | `query` (a 10 character ASIN) | 56 fields including `price`, `brand`, `rating`, `product_details`, `variations` |
| `/api/v1/amazon/pricing` | `asin` | `pricing` array, one entry per seller offer |

Authentication is a header. Send `Authorization: Bearer YOUR_API_KEY` on every request. The `api_key` query parameter still answers but the documentation now marks it deprecated, so build against the header.

**The pricing endpoint takes `asin`, not `query`.** Search and product both take `query`. Pricing does not, and it rejects it with a precise error rather than a guess:

```json
{"errors":{"query":{"asin":["Missing data for required field."],"query":["Unknown field."]}}}
```

A rejected request like that one is billed 0 credits, confirmed by a `spb-cost: 0` response header on the failed call.

### Search

```python
import requests

r = requests.get(
    "https://app.scrapingbee.com/api/v1/amazon/search",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"query": "fitness tracker"},
)
data = r.json()
print(data["products_count"], "products")
```

One page of `fitness tracker` returned 23 products and a `refinements` object carrying every Amazon facet for that query, including `brands`, `band_color`, `battery_average_life` and `case_diameter`. Cost was 5 credits, read off the `spb-cost` header.

### Featured and sponsored products

This is the part CSS selectors cannot give you. Each item in `products` carries its own placement labels:

| Field | Type | What it tells you |
|---|---|---|
| `is_sponsored` | boolean | Paid placement |
| `sponsored_position` | integer or null | Rank within the paid slots |
| `organic_position` | integer or null | Rank within the earned results |
| `is_amazons_choice` | boolean | Amazon's Choice badge |
| `best_seller` | boolean | Best Seller badge |
| `sales_volume` | string | Text such as `10K+ bought in past month` |

So separating paid from earned is a filter, not a parsing problem:

```python
featured = [p for p in data["products"] if p["is_sponsored"]]
organic  = [p for p in data["products"] if not p["is_sponsored"]]
badged   = [p for p in data["products"] if p["is_amazons_choice"] or p["best_seller"]]
```

Across the live `fitness tracker` page, `is_sponsored`, `is_amazons_choice` and `best_seller` all came back with a mix of true and false values, so the labels are populated rather than stubbed. `is_prime` was false on every row of that page, which is worth knowing before you build a Prime filter on top of it.

Sorting is server side too. `sort_by` accepts `featured`, `most_recent`, `price_low_to_high`, `price_high_to_low`, `average_review` and `bestsellers`. The [Amazon featured products API](https://www.scrapingbee.com/scrapers/amazon-featured-products-api/) and [Amazon search API](https://www.scrapingbee.com/scrapers/amazon-search-api/) pages cover the same surface from the product side.

### Product detail

```javascript
const axios = require('axios');

const res = await axios.get('https://app.scrapingbee.com/api/v1/amazon/product', {
  headers: { Authorization: 'Bearer YOUR_API_KEY' },
  params: { query: 'B0GTMTZF3V' },
});
const p = res.data;
console.log(p.brand, p.price, p.currency, p.rating, p.reviews_count);
```

That ASIN was taken from the live search response above rather than invented, and the call returned `brand: "Fitbit"`, `price: 99.99`, `currency: "USD"`, `rating: 4.3`, `reviews_count: 2036`. The full response carries 56 top level keys, including `bullet_points`, `category` as a breadcrumb ladder, `featured_merchant` with the seller id, `rating_stars_distribution`, `sales_rank`, `variations` and `technical_details`.

### Seller offers

```bash
curl "https://app.scrapingbee.com/api/v1/amazon/pricing?asin=B0GTMTZF3V" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Returns a `pricing` array. Each offer has `seller`, `seller_id`, `condition`, `price`, `price_shipping`, `currency`, `rating_count` and a `delivery_options` list. On the ASIN above that was a single Amazon.com offer at 99.99 USD with free delivery.

## Ready made packages

If you want lane two without writing the HTTP layer:

```bash
pip install nocode-amazon
npm install nocode-amazon
```

```python
from nocode_amazon import AmazonScraper

bee = AmazonScraper("YOUR_API_KEY")
page = bee.search("fitness tracker")
for item in bee.featured(page):
    print(item["sponsored_position"], item["title"])
```

## Credit cost

Measured, not quoted:

| Call | Credits |
|---|---|
| Amazon search, default `light_request=true` | 5 per page |
| Amazon search, `light_request=false` | 15 per page |
| Amazon product, default | 5 |
| Amazon product, `light_request=false` | 15 |
| Amazon pricing | 5 |
| Any screenshot request | 15 |
| Rejected request (validation error) | 0 |

Light requests skip the browser. They are the default and they were enough for search, product and pricing in every call made here. Turn them off when you need review text or other content that only appears after JavaScript runs. Plan tiers are on the [pricing page](https://www.scrapingbee.com/pricing).

## Shared parameters

Both `search` and `product` accept `country`, `currency`, `device`, `domain`, `language`, `zip_code`, `add_html`, `screenshot` and `tag`. `search` adds `pages`, `category_id`, `merchant_id`, `sort_by` and `autoselect_variant`. `domain` is how you move marketplaces: `co.uk`, `de`, `in` and so on. `zip_code` matters more than it looks, because Amazon prices and delivery promises are postal code dependent.

Failed requests are retried internally for up to 30 seconds, so set client timeouts above that or you will abandon calls the API is still working on.

## Scope

Public Amazon listing and product pages only. Nothing here signs in, and scraping under login credentials is prohibited by ScrapingBee's terms of service. Amazon's own [Conditions of Use](https://www.amazon.com/gp/help/customer/display.html?nodeId=508088) govern what you may do with the data once you have it, and the [Airtable API](https://airtable.com/developers/web/api/introduction) and [Make](https://www.make.com/en/help/scenarios/scheduling-a-scenario) documentation cover the two tools in lane one.

Full parameter reference: [Amazon API documentation](https://www.scrapingbee.com/documentation/amazon/) and [data extraction rules](https://www.scrapingbee.com/documentation/data-extraction/).

## FAQ

**Can I scrape Amazon without writing code?**
Yes. The Make scenario above is the whole build, and the extraction rules are JSON rather than a program. You still need a ScrapingBee API key and an Airtable base.

**How do I get only the featured products from an Amazon search?**
Filter the `products` array on `is_sponsored`. The endpoint labels every result, so no parsing is involved. `sort_by=featured` changes the ordering Amazon returns.

**Why is my price field empty in the no code lane?**
`span.a-offscreen` moved, or the card you matched has no price because it is an ad unit. This is the failure mode that pushes people to lane two, where prices are parsed server side.

**Which Amazon marketplaces work?**
Any of them, through `domain`. Pass the top level domain, for example `domain=co.uk` or `domain=in`.

## License

MIT. See [LICENSE](LICENSE).
