# Japan Rent Market — 3-Site Cross-Shop Comparison (SUUMO + at home + LIFULL HOME'S)

[![Apify Store](https://img.shields.io/badge/Apify-Store-blue)](https://apify.com/fruitful_quintessence/japan-rent-market-scraper)

**Compare Tokyo 23-ward rental prices across Japan's top 3 property portals in a single dataset.**

Scrapes rental listings from **SUUMO (スーモ)** — Japan's #1 property portal — **at home (アットホーム)** — the #2 portal — and **LIFULL HOME'S (ホームズ)** — the #3 portal. Each item is tagged with its `source` so you can compare rent for the same station/layout across portals.

## Why this is useful

- **Cross-portal price comparison** — the same 1DK near Shibuya station often differs by 5-20% between portals
- **Market research** — track Tokyo rent trends by ward over time
- **Relocation planning** — find the best-priced listing before moving to Japan
- **Investment analysis** — identify underpriced/overpriced areas

## Input

| Field | Type | Default | Description |
|---|---|---|---|
| `ward` | select | `渋谷区` | Tokyo 23 wards (千代田区, 港区, 新宿区, 渋谷区, 世田谷区, etc.) |
| `maxItems` | integer | 100 | Max items to collect |
| `maxPages` | integer | 2 | Max pages per source (LIFULL is page 1 only) |
| `sources` | string | `suumo,athome` | Comma-separated source list (LIFULL is optional — sometimes blocked) |
| `proxyConfiguration` | object | — | Apify proxy |

## Output Sample

```json
{
  "productId": "suumo-渋谷区-クレストコート渋谷笹塚-1DK-2階",
  "title": "クレストコート渋谷笹塚",
  "rent": 158000,
  "managementFee": 12000,
  "deposit": 158000,
  "gratuity": null,
  "layout": "1DK",
  "areaSqm": "28.29m²",
  "floor": "2階",
  "propertyType": "賃貸マンション",
  "address": "東京都渋谷区笹塚3",
  "stations": ["京王線/笹塚駅 歩8分"],
  "buildingAge": "築3年",
  "productUrl": "https://suumo.jp/chintai/jnc_000099005965/",
  "source": "suumo",
  "shop": "SUUMO",
  "ward": "渋谷区"
}
```

The `source` + `shop` fields let you compare the same station/layout across portals.

## Use Cases

- **Cross-portal arbitrage** — find the same building listed cheaper on another portal
- **Rent trend tracking** — schedule daily runs to monitor ward-level rent movements
- **Relocation research** — one dataset covering all 3 major portals

## Pricing

Pay-per-event — **$0.00005/run start + $0.002/item**.

## Data Source

Public rental listings from SUUMO, at home, and LIFULL HOME'S (address, rent, layout, area, station distance).

## Connect

Connect to your workflow via **Apify Connectors**: Google Sheets, Slack, or webhooks — automate rent monitoring without code.
