"""
FINAL rebuild version — College Basketball Scores 2000–2025
Accurate scrape with strict date filters, men’s-only check,
429 handling, resume-safe logic, and OneDrive-safe logging.
"""

import os
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------
BASE_URL = "https://www.sports-reference.com"
OUTPUT_PATH = "C:/Users/lanza/OneDrive/Desktop/college-basketball-scores/scores_clean.csv"

# ✅ Log file outside OneDrive (prevents sync-lock errors)
LOG_PATH = "C:/Users/lanza/college-basketball-scores-logs/scrape_log.txt"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}
OFFSEASON_MONTHS = {5, 6, 7, 8, 9, 10}


# ------------------------------------------
# SAFE REQUEST WITH BACKOFF
# ------------------------------------------
def safe_get(url, headers, retries=4, base_delay=8.0):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers)
            time.sleep(3.1)
        except Exception as e:
            print(f"  ⚠️ Request error: {e}")
            time.sleep(base_delay)
            continue

        if resp.status_code == 200:
            return resp
        if resp.status_code == 429:
            wait = base_delay * (2 ** attempt) + random.uniform(1.0, 3.0)
            print(f"  429 Too Many Requests — sleeping {wait:.1f}s then retrying...")
            time.sleep(wait)
            continue
        print(f"  ⚠️ HTTP {resp.status_code} on {url}")
        return None
    print(f"  ❌  Gave up after {retries} retries on {url}")
    return None


# ------------------------------------------
# SCRAPE A SINGLE DAY
# ------------------------------------------
def scrape_day(target_date: datetime):
    """Scrape all completed men's CBB games for a given date."""
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/cbb/boxscores/?month={target_date.month}&day={target_date.day}&year={target_date.year}"

    print(f"[{date_str}] Fetching {url}")
    resp = safe_get(url, HEADERS)
    if not resp:
        print(f"  ⚠️ Failed to load scoreboard for {date_str}")
        return pd.DataFrame()

    soup = BeautifulSoup(resp.text, "html.parser")
    boxes = soup.select("td.gamelink")
    print(f"  Found {len(boxes)} boxes on page")

    rows = []

    # --- Fallback: old seasons (pre-2004) inline summaries ---
    if target_date.year <= 2003:
        summaries = soup.select("div.game_summary.gender-m")
        for summary in summaries:
            try:
                rows_s = summary.select("table.teams tr")
                if len(rows_s) >= 2:
                    away_row, home_row = rows_s[0], rows_s[1]
                    away_team = away_row.select_one("a").get_text(strip=True)
                    home_team = home_row.select_one("a").get_text(strip=True)
                    away_score = int(away_row.select_one("td.right").get_text(strip=True))
                    home_score = int(home_row.select_one("td.right").get_text(strip=True))
                    rows.append(
                        {
                            "date": date_str,
                            "home_team": home_team,
                            "away_team": away_team,
                            "home": home_score,
                            "away": away_score,
                            "total": home_score + away_score,
                            "margin": home_score - away_score,
                            "ot": False,
                        }
                    )
            except Exception as e:
                print(f"    ⚠️ summary-parse error: {e}")

    for box in boxes:
        a_tag = box.find("a")
        if not a_tag:
            continue
        href = a_tag["href"]

        # Strict date filter
        if f"/cbb/boxscores/{date_str}" not in href:
            continue

        # Skip women’s pages
        classes = box.get("class", [])
        if "women" in href.lower() or any("women" in c.lower() for c in classes):
            continue

        # Skip offseason months
        if target_date.month in OFFSEASON_MONTHS:
            continue

        game_url = BASE_URL + href
        game_page = safe_get(game_url, HEADERS, retries=3, base_delay=3.0)
        if not game_page:
            continue

        g_soup = BeautifulSoup(game_page.text, "html.parser")
        teams = g_soup.select("div.scorebox strong a")
        scores = g_soup.select("div.scorebox div.score")

        # Fallback 1: early 2000s <table class="linescore">
        if len(teams) < 2 or len(scores) < 2:
            alt_table = g_soup.select_one("table.linescore")
            if alt_table:
                rows_alt = alt_table.select("tr")
                if len(rows_alt) >= 2:
                    try:
                        away_cells = rows_alt[0].select("td,th")
                        home_cells = rows_alt[1].select("td,th")
                        away_team = away_cells[0].get_text(strip=True)
                        home_team = home_cells[0].get_text(strip=True)
                        away_score = int(away_cells[-1].get_text(strip=True))
                        home_score = int(home_cells[-1].get_text(strip=True))
                        teams = [away_team, home_team]
                        scores = [away_score, home_score]
                    except Exception:
                        teams, scores = [], []

        # Fallback 2: very old <div class="game_summary gender-m">
        if len(teams) < 2 or len(scores) < 2:
            summary = g_soup.select_one("div.game_summary.gender-m table.teams")
            if summary:
                try:
                    rows_old = summary.select("tr")
                    if len(rows_old) >= 2:
                        away_row, home_row = rows_old[0], rows_old[1]
                        away_team = away_row.select_one("a").get_text(strip=True)
                        home_team = home_row.select_one("a").get_text(strip=True)
                        away_score = int(away_row.select_one("td.right").get_text(strip=True))
                        home_score = int(home_row.select_one("td.right").get_text(strip=True))
                        teams = [away_team, home_team]
                        scores = [away_score, home_score]
                except Exception as e:
                    print(f"    ⚠️ old-format parse error: {e}")
                    teams, scores = [], []

        if len(teams) < 2 or len(scores) < 2:
            continue

        # Normalize names/scores
        home_team = teams[-1] if isinstance(teams[-1], str) else teams[-1].get_text(strip=True)
        away_team = teams[0] if isinstance(teams[0], str) else teams[0].get_text(strip=True)
        try:
            home_score = int(scores[-1]) if isinstance(scores[-1], int) else int(str(scores[-1]).strip())
            away_score = int(scores[0]) if isinstance(scores[0], int) else int(str(scores[0]).strip())
        except ValueError:
            continue

        ot_tag = g_soup.find(string=lambda x: x and "OT" in x)
        is_ot = bool(ot_tag)

        rows.append(
            {
                "date": date_str,
                "home_team": home_team,
                "away_team": away_team,
                "home": home_score,
                "away": away_score,
                "total": home_score + away_score,
                "margin": home_score - away_score,
                "ot": is_ot,
            }
        )

        # polite pause
        time.sleep(random.uniform(3.2, 4.0))

    # No valid games found
    if not rows:
        print(f"  No valid games found for {date_str}")
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as logf:
                logf.write(f"{date_str}: 0 games scraped\n")
        except PermissionError:
            print(f"  ⚠️ Could not write to log (file locked). Skipping log entry.")
        return pd.DataFrame()

    # Build dataframe + dedupe
    df_day = pd.DataFrame(rows).drop_duplicates(
        subset=["date", "home_team", "away_team"], keep="last"
    )

    print(f"  ✅ {len(df_day)} games scraped for {date_str}")

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as logf:
            logf.write(f"{date_str}: {len(df_day)} games scraped\n")
    except PermissionError:
        print(f"  ⚠️ Could not write to log (file locked). Skipping log entry.")

    return df_day


# ------------------------------------------
# APPEND OR CREATE MASTER FILE
# ------------------------------------------
def append_to_master(df_day: pd.DataFrame, out_path: str):
    if df_day.empty:
        return
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    header = not os.path.exists(out_path)
    df_day.to_csv(out_path, mode="a", index=False, header=header)


# ------------------------------------------
# GET DATES ALREADY SCRAPED
# ------------------------------------------
def get_existing_dates(out_path: str):
    if not os.path.exists(out_path):
        return set()
    try:
        df = pd.read_csv(out_path, usecols=["date"])
        return set(df["date"].unique())
    except Exception:
        return set()


# ------------------------------------------
# MAIN DRIVER
# ------------------------------------------
def run_auto_scrape(start_date, end_date):
    existing = get_existing_dates(OUTPUT_PATH)
    current = start_date
    total_days = (end_date - start_date).days + 1

    print(f"\nStarting rebuild: {start_date.date()} -> {end_date.date()}  ({total_days} days)\n")
    print(f"Already scraped: {len(existing)} unique days\n")

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")

        if date_str in existing:
            print(f"[{date_str}] Skipping (already scraped)")
        else:
            df_day = scrape_day(current)
            append_to_master(df_day, OUTPUT_PATH)

        sleep_for = random.uniform(60, 90)
        print(f"  Sleeping {sleep_for:.1f}s before next day...\n")
        time.sleep(sleep_for)

        current += timedelta(days=1)


# ------------------------------------------
# ENTRY POINT — FULL REBUILD 2000–2025
# ------------------------------------------
if __name__ == "__main__":
    run_auto_scrape(datetime(2002, 11, 22), datetime(2025, 11, 6))


# once full 25 year scrape complete, delete code above and replace with below. That will keep the scrape to nightly
# if __name__ == "__main__":    
   # today = datetime.now()
   # yesterday = today - timedelta(days=1)
   # run_auto_scrape(yesterday, yesterday)
