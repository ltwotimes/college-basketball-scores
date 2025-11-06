import asyncio, os, time, random, subprocess
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# CONFIG
CSV_PATH = r"C:\Users\lanza\OneDrive\Desktop\college-basketball-scores\scores.csv"
LOG_PATH = r"C:\Users\lanza\OneDrive\Desktop\college-basketball-scores\logs.txt"
AUTO_GIT_PUSH = True  # Set False if you don’t want nightly Git commits

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

async def scrape_day(date_obj):
    """Scrape all men's games from Sports-Reference for one date."""
    url = f"https://www.sports-reference.com/cbb/boxscores/?month={date_obj.month}&day={date_obj.day}&year={date_obj.year}"
    log(f"📅 {date_obj.date()} — Opening {url}")
    games = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA)
        page = await context.new_page()
        await page.goto(url, timeout=60000)

        try:
            await page.wait_for_selector("div.game_summary", timeout=12000)
        except PWTimeout:
            log("⚠️ Timed out waiting for game summaries, retrying after 3s…")
            await page.reload()
            await page.wait_for_timeout(3000)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    boxes = soup.select("div.game_summary")
    log(f"   ✅ Found {len(boxes)} total boxes on page")

    for box in boxes:
        # detect men's games by /men/ in link or "Men's" in footer
        if "gender-f" in box.get("class", []):
            continue
        if not any("/men/" in (a.get("href") or "").lower() for a in box.select("a[href]")):
            desc = box.get_text(" ", strip=True).lower()
            if "men" not in desc:
                continue

        teams = []
        for tr in box.select("table.teams tr")[:2]:
            tds = tr.select("td")
            if len(tds) >= 1:
                # first <td> always holds the team link
                link = tds[0].select_one("a")
                if link:
                    teams.append(link.get_text(strip=True))

        scores = [int(s.get_text(strip=True))
                  for s in box.select("table.teams td.right")
                  if s.get_text(strip=True).isdigit()][:2]
        if len(teams) != 2 or len(scores) != 2:
            continue

        away, home = teams
        ap, hp = scores
        total = ap + hp
        margin = hp - ap
        ot = 1 if "OT" in box.get_text() else 0
        games.append({
            "date": date_obj.strftime("%Y-%m-%d"),
            "away_team": away,
            "home_team": home,
            "away": ap,
            "home": hp,
            "total": total,
            "margin": margin,
            "ot": ot,
        })

    log(f"   🏀 Collected {len(games)} men's games for {date_obj.date()}")
    return games

def update_csv(new_rows):
    if not new_rows:
        return 0
    df_new = pd.DataFrame(new_rows)
    if os.path.exists(CSV_PATH):
        df_old = pd.read_csv(CSV_PATH)
        combined = pd.concat([df_old, df_new], ignore_index=True)
        combined.drop_duplicates(subset=["date","away_team","home_team","away","home"], inplace=True)
    else:
        combined = df_new
    combined.to_csv(CSV_PATH, index=False)
    return len(df_new)

def next_scrape_date():
    if not os.path.exists(CSV_PATH):
        return datetime(2000, 11, 7)
    df = pd.read_csv(CSV_PATH)
    df["date"] = pd.to_datetime(df["date"])
    last_date = df["date"].max()
    return (last_date + timedelta(days=1)).to_pydatetime()

async def main():
    today = datetime.now()
    # Skip off-season months (May–Oct)
    if today.month not in [11, 12, 1, 2, 3, 4]:
        log("💤 Off-season detected — skipping scrape.")
        return

    start = next_scrape_date()
    if start.date() >= today.date():
        log("✅ Dataset already current.")
        return

    log(f"🚀 Starting scrape for {start.date()}")
    results = await scrape_day(start)

    # Retry if 0 games found
    if len(results) == 0:
        log("⚠️ 0 games found, retrying once in 10 seconds…")
        time.sleep(10)
        results = await scrape_day(start)

    added = update_csv(results)
    log(f"✅ Added {added} new rows to scores.csv")

    if AUTO_GIT_PUSH and added > 0:
        try:
            subprocess.run(["git", "add", "scores.csv"], check=True)
            subprocess.run(["git", "commit", "-m", f"Auto-update {start.date()}"], check=True)
            subprocess.run(["git", "push"], check=True)
            log("☁️  Git push complete")
        except Exception as e:
            log(f"⚠️ Git push failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())