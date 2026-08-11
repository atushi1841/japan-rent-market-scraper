"""
Japan Rent Market — 3サイト横断比較（SUUMO + at home + LIFULL HOME'S）.

東京23区の賃貸物件を3サイトから収集し、同じ駅・同じ間取りの
物件価格を横断比較できるデータセットを出力します。
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def _norm_key(text: str) -> str:
    """Normalize text for case‑insensitive matching."""
    return unicodedata.normalize("NFC", text).casefold().strip()

try:
    from apify import Actor
except ImportError:
    Actor = None

from sources.suumo import search_suumo
from sources.athome import search_athome
from sources.lifull import search_lifull

SOURCES = {
    "suumo": search_suumo,
    "athome": search_athome,
    "lifull": search_lifull,
}


async def run(actor_input: dict) -> list[dict]:
    stats_mode = actor_input.get("statsMode", False)
    ward = str(actor_input.get("ward", "渋谷区")).strip()
    max_items = int(actor_input.get("maxItems", 100))
    max_pages = int(actor_input.get("maxPages", 2))
    sources_str = str(actor_input.get("sources", "suumo,athome"))
    enabled = [s.strip() for s in sources_str.split(",") if s.strip() in SOURCES]

    import httpx

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        results: list[dict] = []
        for name in enabled:
            fn = SOURCES[name]
            try:
                items = await fn(
                    client,
                    ward=ward,
                    max_pages=max_pages,
                    max_items=max_items,
                )
                results.extend(items)
            except Exception as e:
                print(f"Source {name} error: {e}")

    if stats_mode:
        keyword = str(actor_input.get("statsKeyword", "")).strip()
        filtered = []
        for item in results:
            raw_rent = item.get("rent")
            try:
                rent = int(raw_rent)
            except (TypeError, ValueError):
                continue
            if keyword:
                title = str(item.get("title", ""))
                if _norm_key(keyword) not in _norm_key(title):
                    continue
            filtered.append({**item, "rent": rent})

        if filtered:
            rents = [it["rent"] for it in filtered]
            count = len(rents)
            price_min = min(rents)
            price_max = max(rents)
            price_avg = int(sum(rents) / count)
            sorted_rents = sorted(rents)
            if count % 2 == 1:
                price_median = sorted_rents[count // 2]
            else:
                price_median = int((sorted_rents[count // 2 - 1] + sorted_rents[count // 2]) / 2)
            sample_items = [
                {
                    "title": it.get("title", ""),
                    "rent": it.get("rent"),
                    "detailUrl": it.get("detailUrl", ""),
                    "shop": it.get("shop", ""),
                }
                for it in filtered[:3]
            ]
        else:
            count = 0
            price_min = None
            price_max = None
            price_avg = None
            price_median = None
            sample_items = []

        stats_result = {
            "statsType": "japan-rent-price",
            "keyword": keyword,
            "count": count,
            "priceMin": price_min,
            "priceMax": price_max,
            "priceAvg": price_avg,
            "priceMedian": price_median,
            "sampleItems": sample_items,
            "collectedAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        if Actor is not None:
            await Actor.push_data(stats_result)
        else:
            print(json.dumps(stats_result, ensure_ascii=False))
        return results

    if Actor is not None:
        for item in results:
            await Actor.push_data(item)
        print(f"Collected {len(results)} items from {len(enabled)} sources")
    return results


async def main() -> None:
    if Actor is not None:
        async with Actor:
            actor_input = await Actor.get_input() or {}
            await run(actor_input)
    else:
        raw = sys.stdin.read().strip()
        actor_input = json.loads(raw) if raw else {}
        results = await run(actor_input)
        for item in results:
            print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
