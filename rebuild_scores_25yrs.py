import asyncio, csv, time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ---------- CONFIG ----------
OUT_PATH = Path("scores_clean.csv")  # writes NEW clean file so your old scores.csv stays safe
START = datetime(2000, 11, 7)        # agreed start
END   = datetime.today()             # today
PAUSE_SEC = 1.25                     # be polite; adjust if you like
TIMEOUT_MS = 90000
# Only scrape in-season months for CBB (Nov–Apr)
IN_SEASON_MONTHS = {11, 12, 1, 2, 3, 4}
# ---------------------------

def ymd(date_obj):
    return f"{date_obj.year:04d}-{date_obj.month:02d}-{date_obj.day:02d}"

def is_in_season(date_obj):
    return date_obj.month in IN_SEASON_MONTHS

def canon_key(d, home, away, h, a):
    # canonical row key to avoid dupes
    return f"{d}::{home}::{away}::{h}-{a}"

async def fetch_html(page, url):
    await page.goto(url, timeout=TIMEOUT_MS)
    # if the cookie/consent banner exists, try to accept it
    try:
        # common Osano consent selector on SR sites
        await page.locator("button:has-text('Accept')").first.click(timeout=3000)
    except:
        pass
    # wait for boxes or at least the container to appear
    try:
        await page.wait_for_selector("div.game_summaries, div[class*='game_summary']", timeout=8000)
    except:
        # proceed anyway — sometimes it’s already in HTML
        pass
    return await page.content()

def parse_day(html, date_obj):
    """Parse only MEN'S games whose boxscore link contains the exact date."""
    soup = BeautifulSoup(html, "html.parser")
    boxes = soup.select("div.game_summary")
    wanted_date = ymd(date_obj)

    games = []
    for box in boxes:
        classes = set(box.get("class") or [])
        # MEN'S filter: either explicit gender-m or the "Men's" descriptor row
        is_mens = ("gender-m" in classes) or ("Men's" in box.get_text(" ", strip=True))
        if not is_mens:
            continue

        # link with exact date in href, e.g. /cbb/boxscores/2000-11-09-...
        a = box.select_one("td.gamelink a[href*='/cbb/boxscores/']")
        if not a:
            continue
        href = a.get("href", "")
        if wanted_date not in href:
            # This is the critical guard: ignore boxes that aren't from the requested day
            continue

        # Extract teams and scores from the table
        trows = box.select("table.teams tr")
        if len(trows) < 2:
            continue

        def row_to_team_score(tr):
            tname_el = tr.select_one("td a[href*='/cbb/schools/']")
            tname = (tname_el.get_text(strip=True) if tname_el else "").strip()
            # ensure it's a men's program link if present
            if tname_el and "/men/" not in tname_el.get("href",""):
                return None, None  # skip if it's not men's
            # score cell
            sc_el = tr.select_one("td.right")
            try:
                sc = int((sc_el.get_text(strip=True) if sc_el else "").strip())
            except:
                sc = None
            return tname, sc

        t1, s1 = row_to_team_score(trows[0])
        t2, s2 = row_to_team_score(trows[1])

        # Must have both names and integer scores
        if not t1 or not t2 or s1 is None or s2 is None:
            continue

        # Identify home/away (Sports-Reference lists winner/loser; use the line order as away/home convention):
        # Historically on SR, the first row is loser/winner but NOT always away/home; safer to treat the 1st as away
        away_team, home_team = t1, t2
        away, home = s1, s2

        total = home + away
        margin = home - away
        ot = 1 if "OT" in box.get_text(" ", strip=True) else 0

        games.append({
            "date": date_obj.strftime("%-m/%-d/%Y") if hasattr(datetime, "fromisoformat") else date_obj.strftime("%m/%d/%Y"),
            "home_team": home_team,
            "away_team": away_team,
            "home": home,
            "away": away,
            "total": total,
            "margin": margin,
            "ot": ot
        })

    # Drop exact dupes within the day (paranoia)
    if games:
        df = pd.DataFrame(games).drop_duplicates(subset=["home_team","away_team","home","away"])
        games = df.to_dict("records")

    return games

async def scrape_range():
    # Init output (new file)
    write_header = True
    if OUT_PATH.exists():
        OUT_PATH.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        d = START
        total_rows = 0
        while d <= END:
            if not is_in_season(d):
                d += timedelta(days=1)
                continue

            url = f"https://www.sports-reference.com/cbb/boxscores/?month={d.month}&day={d.day}&year={d.year}"
            print(f"📅 {d.date()} — {url}")

            html = await fetch_html(page, url)
            # hard guard for stub/off-season content
            if "no box scores" in html.lower():
                print("  ↪ No box scores message on page; skipping.")
                d += timedelta(days=1); time.sleep(0.1); continue

            games = parse_day(html, d)
            print(f"  ✅ Kept {len(games)} men’s games (date-strict)")

            if games:
                # append to CSV as we go (safe on long runs)
                with OUT_PATH.open("a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(games[0].keys()))
                    if write_header:
                        w.writeheader()
                        write_header = False
                    w.writerows(games)
                total_rows += len(games)

            time.sleep(PAUSE_SEC)
            d += timedelta(days=1)

        await browser.close()
    print(f"\n✅ Done. Wrote {total_rows} rows to {OUT_PATH.resolve()}")

if __name__ == "__main__":
    asyncio.run(scrape_range())
