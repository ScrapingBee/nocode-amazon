// Split an Amazon search page into featured (sponsored) and organic results.
// Verified against the live ScrapingBee Amazon API on 2026-09-10.
// Set SCRAPINGBEE_API_KEY in your environment before running.

const axios = require('axios');

const BASE = 'https://app.scrapingbee.com/api/v1';
const KEY = process.env.SCRAPINGBEE_API_KEY;
const headers = { Authorization: `Bearer ${KEY}` };

async function search(query, params = {}) {
  const res = await axios.get(`${BASE}/amazon/search`, {
    headers,
    params: { query, ...params },
    timeout: 60000,
  });
  return res.data;
}

async function product(asin, params = {}) {
  // The product endpoint takes 'query', which accepts a 10 character ASIN.
  const res = await axios.get(`${BASE}/amazon/product`, {
    headers,
    params: { query: asin, ...params },
    timeout: 60000,
  });
  return res.data;
}

async function pricing(asin, params = {}) {
  // The pricing endpoint takes 'asin'. Sending 'query' here returns a validation error.
  const res = await axios.get(`${BASE}/amazon/pricing`, {
    headers,
    params: { asin, ...params },
    timeout: 60000,
  });
  return res.data;
}

(async () => {
  const page = await search('fitness tracker', { sort_by: 'featured' });

  const featured = page.products.filter((p) => p.is_sponsored);
  const organic = page.products.filter((p) => !p.is_sponsored);

  console.log(`${page.products_count} products, ${featured.length} featured, ${organic.length} organic`);

  featured.forEach((p) => {
    console.log(`  ad  slot ${p.sponsored_position}  ${p.price} ${p.currency}  ${p.title.slice(0, 60)}`);
  });

  organic.slice(0, 5).forEach((p) => {
    const badge = p.is_amazons_choice ? 'choice' : p.best_seller ? 'bestseller' : '';
    console.log(`  org rank ${p.organic_position}  ${p.price} ${p.currency}  ${badge}`);
  });

  if (organic.length) {
    const asin = organic[0].asin;
    const detail = await product(asin);
    console.log(`\n${detail.brand} / ${detail.price} ${detail.currency} / ${detail.rating} stars`);
    const offers = await pricing(asin);
    offers.pricing.forEach((o) => console.log(`  offer ${o.seller}  ${o.price}  ${o.condition}`));
  }
})();
