#!/usr/bin/env python3
"""
IDAC 県別・全国ランキング中継データ生成スクリプト

公式APIはブラウザからCORSで読めないため、このスクリプトでサーバー側取得し
GitHub Pages 等に enrich.json として公開します。

使い方:
  python3 fetch_enrich.py
  → enrich.json を出力

環境変数:
  ROUND   ラウンド番号（省略時は currentRoundInfo を参照）
  OUT     出力パス（省略時 enrich.json）
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
BASE = "https://initiald.sega.jp/inidac/json/ranking/v1"
TRACKER_URL = "https://attack-racing.github.io/idac-ob-tracker-jpn/data.json"


def fetch_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "idac-relay/1.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def name_key(s: str) -> str:
    out = []
    for ch in str(s or ""):
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:
            out.append(chr(o - 0xFEE0))
        elif ch == "　":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out).lower().replace(" ", "")


def normalize_record(r: dict) -> dict:
    return {
        "name": r.get("name") or "",
        "shop": r.get("shopname") or r.get("shop") or "",
        "car": r.get("carname") or r.get("car") or "",
        "point": int(r.get("point") or 0),
        "pridePoint": int(r.get("pridePoint") or 0),
        "prideId": r.get("prideId") or "",
        "onlineBattleRankId": r.get("onlineBattleRankId") or "",
        "starCnt": int(r.get("starCnt") or 0),
        "mytitleId": r.get("mytitleId") or "",
        "updateDate": r.get("updateDate") or "",
    }


def merge_rec(a: dict, b: dict) -> dict:
    """a に b をマージ（詳細フィールドはより良い方を残す）"""
    if not a:
        return b
    if not b:
        return a
    return {
        "name": a.get("name") or b.get("name") or "",
        "shop": a.get("shop") or b.get("shop") or "",
        "car": a.get("car") or b.get("car") or "",
        "point": max(int(a.get("point") or 0), int(b.get("point") or 0)),
        "pridePoint": max(int(a.get("pridePoint") or 0), int(b.get("pridePoint") or 0)),
        "prideId": a.get("prideId") or b.get("prideId") or "",
        "onlineBattleRankId": a.get("onlineBattleRankId") or b.get("onlineBattleRankId") or "",
        "starCnt": max(int(a.get("starCnt") or 0), int(b.get("starCnt") or 0)),
        "mytitleId": a.get("mytitleId") or b.get("mytitleId") or "",
        "updateDate": a.get("updateDate") or b.get("updateDate") or "",
    }


# 店舗名 → 都道府県 areaId（優先取得用）
SHOP_AREA_RULES = [
    (["北海道", "札幌", "函館", "旭川"], 0),
    (["青森"], 1),
    (["岩手", "盛岡"], 2),
    (["宮城", "仙台"], 3),
    (["福島", "郡山"], 4),
    (["山形"], 5),
    (["秋田"], 6),
    (["茨城", "水戸", "つくば"], 7),
    (["栃木", "宇都宮"], 8),
    (["群馬", "高崎", "前橋"], 9),
    (["千葉", "船橋", "柏"], 10),
    (["埼玉", "大宮", "浦和", "川口", "所沢", "川越"], 11),
    (["東京", "池袋", "新宿", "渋谷", "秋葉", "立石", "中野", "町田"], 12),
    (["神奈川", "横浜", "川崎", "平塚", "藤沢", "厚木", "相模原"], 13),
    (["山梨", "甲府"], 14),
    (["新潟"], 15),
    (["長野", "松本", "諏訪"], 16),
    (["富山"], 17),
    (["石川", "金沢"], 18),
    (["愛知", "名古屋", "豊橋", "豊田"], 19),
    (["静岡", "浜松", "沼津"], 20),
    (["岐阜"], 21),
    (["三重", "四日市"], 22),
    (["福井"], 23),
    (["大阪", "なんば", "梅田"], 24),
    (["京都"], 25),
    (["奈良"], 26),
    (["滋賀", "草津"], 27),
    (["和歌山"], 28),
    (["兵庫", "神戸", "姫路"], 29),
    (["広島"], 30),
    (["鳥取"], 31),
    (["島根"], 32),
    (["岡山"], 33),
    (["山口"], 34),
    (["徳島"], 35),
    (["香川", "高松"], 36),
    (["愛媛", "松山"], 37),
    (["高知"], 38),
    (["福岡", "博多", "北九州"], 39),
    (["佐賀"], 40),
    (["長崎"], 41),
    (["熊本"], 42),
    (["大分"], 43),
    (["宮崎"], 44),
    (["鹿児島"], 45),
    (["沖縄", "那覇"], 46),
]


def guess_areas(shop: str) -> list[int]:
    s = shop or ""
    ids = []
    for keys, aid in SHOP_AREA_RULES:
        if any(k in s for k in keys):
            ids.append(aid)
    return ids


def main():
    out_path = os.environ.get("OUT", "enrich.json")
    round_id = os.environ.get("ROUND")

    if not round_id:
        try:
            info = fetch_json(f"{BASE}/currentRoundInfo.json")
            if isinstance(info, (int, str)):
                round_id = str(info)
            elif isinstance(info, dict):
                round_id = str(info.get("round") or info.get("currentRound") or "76")
            else:
                round_id = "76"
        except Exception:
            round_id = "76"

    print(f"[idac-relay] round={round_id}")

    # トラッカーのアクティブ勢（優先して県別補完）
    wanted: dict[str, dict] = {}
    tracker_time = None
    try:
        tr = fetch_json(TRACKER_URL)
        tracker_time = tr.get("trackerTime")
        for plist in (tr.get("ranks") or {}).values():
            for p in plist or []:
                wanted[name_key(p.get("name"))] = p
        print(f"[idac-relay] tracker actives={len(wanted)} time={tracker_time}")
    except Exception as e:
        print(f"[idac-relay] tracker fetch failed: {e}")

    # 全国 TOP1000
    rp = fetch_json(f"{BASE}/roundPoint/rp_round-{round_id}_area-all.json")
    by_name: dict[str, dict] = {}
    for r in rp.get("records") or []:
        k = name_key(r.get("name"))
        by_name[k] = normalize_record(r)

    # トラッカー勢で全国にいない / 星やPRIDEが薄い人を県別で探す
    need_area: set[str] = set()
    for k, p in wanted.items():
        rec = by_name.get(k)
        rank = p.get("rank") or ""
        if not rec:
            need_area.add(k)
        elif rank == "Pride" and not (rec.get("pridePoint") or 0) > 0:
            need_area.add(k)
        elif rank in ("Ruby", "Sapphire", "Emerald") and not (rec.get("starCnt") or 0) > 0:
            need_area.add(k)

    print(f"[idac-relay] need_area={len(need_area)}")

    # 店舗から県を推定して優先順
    priority: list[int] = []
    seen: set[int] = set()
    for k in need_area:
        shop = (wanted.get(k) or {}).get("shop") or (by_name.get(k) or {}).get("shop") or ""
        for aid in guess_areas(shop):
            if aid not in seen:
                seen.add(aid)
                priority.append(aid)
    area_order = priority + [i for i in range(0, 47) if i not in seen]

    for area in area_order:
        if not need_area:
            break
        url = f"{BASE}/roundPoint/rp_round-{round_id}_area-{area}.json"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"[idac-relay] area {area} fail: {e}")
            continue
        for r in data.get("records") or []:
            k = name_key(r.get("name"))
            if k not in need_area and k not in wanted:
                continue
            rec = normalize_record(r)
            by_name[k] = merge_rec(by_name.get(k), rec)
            if k in need_area:
                # 必要情報が埋まったら除外
                got = by_name[k]
                p = wanted.get(k) or {}
                rank = p.get("rank") or ""
                ok = True
                if rank == "Pride" and not (got.get("pridePoint") or 0) > 0 and not got.get("prideId"):
                    ok = False
                if rank in ("Ruby", "Sapphire", "Emerald") and not (got.get("starCnt") or 0) > 0:
                    # 星0が正しい場合もあるので、レコード自体は取れたら除外
                    ok = True
                if ok:
                    need_area.discard(k)
                    print(
                        f"  area-{area} {got['name']} pp={got['pridePoint']} star={got['starCnt']}"
                    )
        time.sleep(0.08)

    # 出力は「トラッカー勢 + 直近更新の全国勢」に絞ると軽い
    records = []
    for k, rec in by_name.items():
        if k in wanted:
            records.append(rec)

    # トラッカーにいないが、念のため wanted 以外は出さない（軽量中継）
    out = {
        "generatedAt": datetime.now(JST).strftime("%Y/%m/%d %H:%M:%S"),
        "round": str(round_id),
        "nationalCalcDate": rp.get("calcDate"),
        "trackerTime": tracker_time,
        "count": len(records),
        "records": records,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[idac-relay] wrote {out_path} count={len(records)} still_need={len(need_area)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
