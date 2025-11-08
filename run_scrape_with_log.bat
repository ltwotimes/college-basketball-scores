@echo off
chcp 65001 >nul
cd /d "C:\Users\lanza\OneDrive\Desktop\college-basketball-scores"

echo ======== Starting scrape at %date% %time% ======== >> "C:\Users\lanza\college-basketball-scores-logs\scrape_log.txt"

"C:\Users\lanza\AppData\Local\Programs\Python\Python311\python.exe" "C:\Users\lanza\OneDrive\Desktop\college-basketball-scores\final_scores_scraper_auto.py" >> "C:\Users\lanza\college-basketball-scores-logs\scrape_log.txt" 2>&1

echo ======== Finished run at %date% %time% ======== >> "C:\Users\lanza\college-basketball-scores-logs\scrape_log.txt"
pause
