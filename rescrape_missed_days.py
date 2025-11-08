import pandas as pd
import os
from datetime import datetime, timedelta
from final_scores_scraper_auto import scrape_day, append_to_master, OUTPUT_PATH

LOG_FILE = "scrape_log.txt"

def find_failed_days(log_path):
    if not os.path.exists(log_path):
        print("No log found.")
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    failed = []
    for line in lines:
        if "0 games scraped" in line or "Failed to load" in line or "❌" in line:
            try:
                date_str = line.split(":")[0].strip("[] ")
                datetime.strptime(date_str, "%Y-%m-%d")
                failed.append(date_str)
            except:
                pass
    return sorted(set(failed))

def rescrape_failed_days():
    failed = find_failed_days(LOG_FILE)
    if not failed:
        print("✅ No failed days found.")
        return

    print(f"🔁 Re-scraping {len(failed)} missed days...")
    for date_str in failed:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        df_day = scrape_day(d)
        append_to_master(df_day, OUTPUT_PATH)
    print("✅ Done re-scraping missed days!")

if __name__ == "__main__":
    rescrape_failed_days()
