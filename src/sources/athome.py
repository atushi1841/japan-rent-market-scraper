"""
at home (athome.co.jp) 賃貸スクレイパー.

検索ページ: /chintai/tokyo/shibuya-city/list/
ページネーション: /chintai/tokyo/shibuya-city/list/page{n}/
物件カード構造（実HTMLから確認済み）:
  <div class="p-property p-property--building js-block">
    <h2 class="p-property__name">ＭＹ　ＭＡＩＳＯＮ 3階建</h2>
    住所: <p class="p-property__address">渋谷区西原１丁目</p>
    駅: <div class="p-property__access">京王線 「幡ヶ谷」駅 徒歩3分</div>
    賃料: <div class="p-property__information-rent">15.8万円</div>
    管理費: <div class="p-property__information-other">12000円</div>
    間取り: <div class="p-property__room-floorplan">1DK</div>
    面積: <div class="p-property__room-information">28.29m²</div>
    礼金: <div class="p-property__room-keymoney">-</div>
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.athome.co.jp"
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
    if raw in ("-", "―", "", "無料", "0"):
        return None
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
    for prop in soup.select("div.p-property--building"):
        # 物件名
        name_el = prop.select_one(".p-property__name, h2")
        title = name_el.get_text(strip=True) if name_el else ""
        if not title:
            continue
        # 物件リンク
        link_el = prop.select_one("a[href*='bukken']")
        link = ""
        if link_el:
            link = str(link_el.get("href", "") or "")
            if link.startswith("/"):
                link = BASE_URL + link
        # 住所
        address = ""
        addr_el = prop.select_one(".p-property__address")
        if addr_el:
            address = addr_el.get_text(strip=True)
        # 駅
        stations = []
        for acc in prop.select(".p-property__access div, .p-property__access li"):
            t = acc.get_text(strip=True)
            if t and "駅" in t:
                stations.append(t)
        # 種別・築年（donelist）
        property_type = ""
        building_age = ""
        floors = ""
        donelist = prop.select_one(".p-property__donelist--building")
        if donelist:
            for li in donelist.select("li"):
                t = li.get_text(strip=True)
                if "賃貸" in t:
                    property_type = t
                elif "築" in t:
                    building_age = t
                elif "階建" in t:
                    floors = t
        # 賃料
        rent_el = prop.select_one(".p-property__information-rent")
        rent = _clean_price(rent_el.get_text(strip=True)) if rent_el else None
        # 管理費
        admin = None
        other_el = prop.select_one(".p-property__information-other")
        if other_el:
            admin = _clean_price(other_el.get_text(strip=True))
        # 部屋（複数ある場合の最初の部屋）
        room = prop.select_one(".p-property__room--detail-information, .p-property__room--detailbox")
        layout = ""
        area = ""
        floor = ""
        deposit = None
        gratuity = None
        if room:
            fp = room.select_one(".p-property__room-floorplan")
            layout = fp.get_text(" ", strip=True) if fp else ""
            # 階
            fl = room.select_one(".p-property__floor")
            if fl:
                floor = fl.get_text(strip=True)
            # 賃料・管理費（"11.9 万円 8,000円" が1つのli内）
            rr = room.select_one("li.p-property__room-rent")
            if rr:
                rent_txt = rr.get_text(" ", strip=True)
                # 最初の万円が賃料、続く円が管理費
                rent_m = re.search(r"([\d.]+)\s*万円", rent_txt)
                if rent_m:
                    rent = int(float(rent_m.group(1)) * 10000)
                admin_m = re.search(r"([\d,]+)\s*円", rent_txt)
                if admin_m:
                    admin = int(admin_m.group(1).replace(",", ""))
            # 管理費（部屋行の別セル）
            for li in room.select(".p-property__room--information-list li, .p-property__room--information li"):
                t = li.get_text(" ", strip=True)
                if "円" in t and ("管理" in t or "共益" in t):
                    admin = _clean_price(t)
                elif "㎡" in t or "m²" in t:
                    area = t
            # 敷金・礼金（"1ヶ月" 等の月数形式）
            km = room.select_one(".p-property__room-keymoney")
            if km:
                km_texts = [x.get_text(" ", strip=True) for x in km.select("li, div, span") if x.get_text(" ", strip=True)]
                joined = " ".join(km_texts)
                if "礼金" in joined:
                    g = km.select_one(".shikirei_text_paid")
                    gratuity = g.get_text(" ", strip=True) if g else joined
                elif "敷金" in joined:
                    d = km.select_one(".shikirei_text_paid")
                    deposit = d.get_text(" ", strip=True) if d else joined
        if rent is None and not layout:
            # 物件ブロックにはあるが部屋詳細がない場合はスキップ（空ブロック対策）
            if not title:
                continue
        items.append({
            "productId": f"athome-{ward}-{title}-{layout}-{len(items)}",
            "title": title,
            "rent": rent,
            "managementFee": admin,
            "deposit": deposit,
            "gratuity": gratuity,
            "layout": layout,
            "areaSqm": area,
            "floor": floor,
            "propertyType": property_type,
            "address": address,
            "stations": stations,
            "buildingAge": building_age,
            "buildingFloors": floors,
            "productUrl": link or BASE_URL,
            "source": "athome",
            "shop": "at home",
            "ward": ward,
        })
    return items


async def search_athome(
    client: httpx.AsyncClient,
    ward: str = "渋谷区",
    max_pages: int = 2,
    max_items: int = 100,
) -> list[dict]:
    if ward not in TOKYO_WARDS:
        ward = "渋谷区"
    wurl = TOKYO_WARDS[ward]
    base = f"{BASE_URL}/chintai/tokyo/{wurl}/list/"
    results: list[dict] = []
    page = 1
    while page <= max_pages and len(results) < max_items:
        url = base if page == 1 else f"{base}page{page}/"
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
        if f"page{page+1}/" not in html:
            break
        page += 1
        await asyncio.sleep(0.5)
    return results
