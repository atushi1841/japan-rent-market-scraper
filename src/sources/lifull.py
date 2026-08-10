"""
LIFULL HOME'S (homes.co.jp) 賃貸スクレイパー.

検索ページ: /chintai/tokyo/shibuya-city/
※ ページネーションはJSレンダリングのため1ページ目のみ取得（約20件）
物件カード構造（実HTMLから確認済み）:
  <div class="bukkenList">
    <h2 class="bukkenName prg-bukkenName">ACT SOHO KEIO笹塚</h2>
    賃料: 19万円
    駅: 笹塚駅 徒歩4分
    面積: 40.17m²
    間取り: 1DK
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.homes.co.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 東京23区のURL
TOKYO_WARDS = {
    "千代田区": "chiyoda-city",
    "中央区": "chuo-city",
    "港区": "minato-city",
    "新宿区": "shinjuku-city",
    "文京区": "bunkyo-city",
    "台東区": "taito-city",
    "墨田区": "sumida-city",
    "江東区": "koto-city",
    "品川区": "shinagawa-city",
    "目黒区": "meguro-city",
    "大田区": "ota-city",
    "世田谷区": "setagaya-city",
    "渋谷区": "shibuya-city",
    "中野区": "nakano-city",
    "杉並区": "suginami-city",
    "豊島区": "toshima-city",
    "北区": "kita-city",
    "荒川区": "arakawa-city",
    "板橋区": "itabashi-city",
    "練馬区": "nerima-city",
    "足立区": "adachi-city",
    "葛飾区": "katsushika-city",
    "江戸川区": "edogawa-city",
}


async def fetch_page(client: httpx.AsyncClient, url: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            resp = await client.get(url, headers=HEADERS, follow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
            if resp.status_code in (403, 429):
                await asyncio.sleep(3 * (attempt + 1))
                continue
            return None
        except httpx.HTTPError:
            await asyncio.sleep(2 * (attempt + 1))
    return None


def _clean_price(raw: str) -> Optional[int]:
    raw = raw.strip().replace(",", "")
    m = re.search(r"([\d.]+)万円", raw)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"([\d,]+)円", raw)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def parse_items(html: str, ward: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # 物件名（bukkenName）
    for name_el in soup.select(".bukkenName"):
        title = name_el.get_text(strip=True)
        if not title:
            continue
        # 物件ブロック（親のliなど）
        block = name_el.find_parent(["li", "div"])
        link = ""
        if block:
            a = block.find("a", href=True)
            if a:
                href = str(a.get("href", ""))
                if href.startswith("/"):
                    link = BASE_URL + href
        # 賃料（¥表示や「19万円」）
        rent = None
        admin = None
        layout = ""
        area = ""
        station = ""
        address = ""
        property_type = ""
        if block:
            txt = block.get_text(" ", strip=True)
            # 賃料: 最初の万円
            m = re.search(r"([\d.]+)万円", txt)
            if m:
                rent = int(float(m.group(1)) * 10000)
            # 間取り: 1K/1DK/2LDK等
            m2 = re.search(r"\d+(?:LDK|DK|K|R)\+?S?", txt)
            if m2:
                layout = m2.group(0)
            # 面積
            m3 = re.search(r"([\d.]+)m²", txt)
            if m3:
                area = m3.group(0)
            # 駅
            m4 = re.search(r"([^ ]+駅[^ ]*徒歩\d+分)", txt)
            if m4:
                station = m4.group(1)
            # 種別
            for t in ["賃貸マンション", "賃貸アパート", "賃貸戸建て", "賃貸テラスハウス"]:
                if t in txt:
                    property_type = t
                    break
        if rent is None and not layout:
            continue
        items.append({
            "productId": f"lifull-{ward}-{title}-{layout}-{len(items)}",
            "title": title,
            "rent": rent,
            "managementFee": admin,
            "deposit": None,
            "gratuity": None,
            "layout": layout,
            "areaSqm": area,
            "floor": "",
            "propertyType": property_type,
            "address": address,
            "stations": [station] if station else [],
            "buildingAge": "",
            "buildingFloors": "",
            "productUrl": link or BASE_URL,
            "source": "lifull",
            "shop": "LIFULL HOME'S",
            "ward": ward,
        })
    return items


async def search_lifull(
    client: httpx.AsyncClient,
    ward: str = "渋谷区",
    max_pages: int = 1,  # ページネーションはJSのため1ページ目のみ
    max_items: int = 50,
) -> list[dict]:
    if ward not in TOKYO_WARDS:
        ward = "渋谷区"
    wurl = TOKYO_WARDS[ward]
    url = f"{BASE_URL}/chintai/tokyo/{wurl}/"
    results: list[dict] = []
    html = await fetch_page(client, url)
    if html:
        items = parse_items(html, ward)
        for it in items[:max_items]:
            it["scrapedAt"] = __import__("datetime").datetime.now().isoformat() + "Z"
            results.append(it)
    return results
