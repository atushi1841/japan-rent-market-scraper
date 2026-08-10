"""
SUUMO (suumo.jp) 賃貸スクレイパー.

検索ページ: /chintai/tokyo/sc_shibuya/ （東京都渋谷区など区単位URL）
ページネーション: ?page={n}
物件カード構造:
  <div class="cassetteitem">
    <div class="cassetteitem_content-title">クレストコート渋谷笹塚</div>
    <div class="cassetteitem_detail-text">京王線/笹塚駅 歩8分</div>
    住所: 東京都渋谷区笹塚3
    賃料: <span class="cassetteitem_price cassetteitem_price--rent">15.8万円</span>
    管理費: <span class="cassetteitem_price cassetteitem_price--administration">12000円</span>
    敷金: <span class="cassetteitem_price cassetteitem_price--deposit">15.8万円</span>
    礼金: <span class="cassetteitem_price cassetteitem_price--gratuity">-</span>
    間取り: <span class="cassetteitem_madori">1DK</span>
    面積: <span class="cassetteitem_menseki">28.29m<sup>2</sup></span>
    階: <td>3階</td>
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://suumo.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 東京23区の区URL（sc_XXXX形式）
TOKYO_WARDS = {
    "千代田区": "sc_chiyoda",
    "中央区": "sc_chuo",
    "港区": "sc_minato",
    "新宿区": "sc_shinjuku",
    "文京区": "sc_bunkyo",
    "台東区": "sc_taito",
    "墨田区": "sc_sumida",
    "江東区": "sc_koto",
    "品川区": "sc_shinagawa",
    "目黒区": "sc_meguro",
    "大田区": "sc_ota",
    "世田谷区": "sc_setagaya",
    "渋谷区": "sc_shibuya",
    "中野区": "sc_nakano",
    "杉並区": "sc_suginami",
    "豊島区": "sc_toshima",
    "北区": "sc_kita",
    "荒川区": "sc_arakawa",
    "板橋区": "sc_itabashi",
    "練馬区": "sc_nerima",
    "足立区": "sc_adachi",
    "葛飾区": "sc_katsushika",
    "江戸川区": "sc_edogawa",
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
    """'15.8万円' → 158000 / '12000円' → 12000 / '-' → None"""
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
    for cassette in soup.select("div.cassetteitem"):
        # 物件名
        title_el = cassette.select_one(".cassetteitem_content-title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue
        # 物件リンク
        link_el = cassette.select_one("a[href*='/chintai/jnc_']")
        link = ""
        if link_el:
            link = str(link_el.get("href", "") or "")
            if link.startswith("/"):
                link = BASE_URL + link
        # 種別（賃貸マンション/アパート）
        type_el = cassette.select_one(".cassetteitem_content-label")
        btype = type_el.get_text(strip=True) if type_el else ""
        # 住所
        addr_el = cassette.select_one(".cassetteitem_detail-col1")
        address = ""
        if addr_el:
            for div in addr_el.select("div"):
                t = div.get_text(strip=True)
                if t and "都" in t or "区" in t:
                    address = t
                    break
        # 駅情報（複数）
        station_el = cassette.select_one(".cassetteitem_detail-col2")
        stations = []
        if station_el:
            for div in station_el.select("div"):
                t = div.get_text(strip=True)
                if t:
                    stations.append(t)
        # 築年・階数
        build_el = cassette.select_one(".cassetteitem_detail-col3")
        build_year = ""
        floors = ""
        if build_el:
            texts = [d.get_text(strip=True) for d in build_el.select("div") if d.get_text(strip=True)]
            for t in texts:
                if "築" in t:
                    build_year = t
                elif "階" in t and "建" in t:
                    floors = t
        # 部屋テーブル（複数行あり）
        room_rows = cassette.select("tr.js-table-cassette")
        if not room_rows:
            room_rows = cassette.select("tr")
        for row in room_rows:
            tds = row.select("td")
            if len(tds) < 5:
                continue
            floor = tds[0].get_text(strip=True)
            rent_el = row.select_one(".cassetteitem_price--rent")
            admin_el = row.select_one(".cassetteitem_price--administration")
            deposit_el = row.select_one(".cassetteitem_price--deposit")
            gratuity_el = row.select_one(".cassetteitem_price--gratuity")
            madori_el = row.select_one(".cassetteitem_madori")
            area_el = row.select_one(".cassetteitem_menseki")
            rent = _clean_price(rent_el.get_text(strip=True)) if rent_el else None
            admin = _clean_price(admin_el.get_text(strip=True)) if admin_el else None
            deposit = _clean_price(deposit_el.get_text(strip=True)) if deposit_el else None
            gratuity = _clean_price(gratuity_el.get_text(strip=True)) if gratuity_el else None
            madori = madori_el.get_text(strip=True) if madori_el else ""
            area = area_el.get_text(strip=True) if area_el else ""
            if rent is None and not madori:
                continue
            items.append({
                "productId": f"suumo-{ward}-{title}-{madori}-{floor}",
                "title": title,
                "rent": rent,
                "managementFee": admin,
                "deposit": deposit,
                "gratuity": gratuity,
                "layout": madori,
                "areaSqm": area,
                "floor": floor,
                "propertyType": btype,
                "address": address,
                "stations": stations,
                "buildingAge": build_year,
                "buildingFloors": floors,
                "productUrl": link,
                "source": "suumo",
                "shop": "SUUMO",
                "ward": ward,
            })
    return items


async def search_suumo(
    client: httpx.AsyncClient,
    ward: str = "渋谷区",
    max_pages: int = 2,
    max_items: int = 100,
) -> list[dict]:
    if ward not in TOKYO_WARDS:
        ward = "渋谷区"
    sc = TOKYO_WARDS[ward]
    base = f"{BASE_URL}/chintai/tokyo/{sc}/"
    results: list[dict] = []
    page = 1
    while page <= max_pages and len(results) < max_items:
        url = f"{base}?page={page}"
        html = await fetch_page(client, url)
        if not html:
            break
        items = parse_items(html, ward)
        if not items:
            break
        for it in items:
            if len(results) >= max_items:
                break
            it["scrapedAt"] = __import__("datetime").datetime.now().isoformat() + "Z"
            results.append(it)
        if "?page=" not in html or f"page={page+1}" not in html:
            break
        page += 1
        await asyncio.sleep(0.5)
    return results
