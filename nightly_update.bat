@echo off
setlocal enabledelayedexpansion

cd /d "C:\Users\lanza\OneDrive\Desktop\college-basketball-scores"

echo ===================================================== >> nightly_log.txt
echo ======== Starting nightly update at %date% %time% ======== >> nightly_log.txt
echo. >> nightly_log.txt

:: Run scraper (incremental once you're ready)
python final_scores_scraper_auto.py >> nightly_log.txt 2>&1

echo. >> nightly_log.txt
echo -------- Scrape complete, pushing to GitHub... -------- >> nightly_log.txt
echo. >> nightly_log.txt

:: Stage changes
git add scores_clean.csv dashboard.py final_scores_scraper_auto.py >> nightly_log.txt 2>&1

:: Commit with timestamp
set commitmsg=Auto update: %date% %time%
git commit -m "%commitmsg%" >> nightly_log.txt 2>&1

:: Sync with remote
git pull origin main --rebase >> nightly_log.txt 2>&1
git push origin main --force >> nightly_log.txt 2>&1

echo. >> nightly_log.txt
echo -------- Git push completed successfully -------- >> nightly_log.txt
echo Finished at %date% %time% >> nightly_log.txt
echo ===================================================== >> nightly_log.txt
echo. >> nightly_log.txt

endlocal
exit
