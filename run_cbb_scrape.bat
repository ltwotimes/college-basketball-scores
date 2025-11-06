@echo off
cd "C:\Users\lanza\OneDrive\Desktop\college-basketball-scores"
echo ================================================== >> logs.txt
echo Starting update run at %date% %time% >> logs.txt

REM Run daily update script
python update_scores_yesterday.py >> logs.txt 2>&1

REM Commit and push to GitHub
git add scores.csv >> logs.txt 2>&1
git commit -m "Auto-update from Task Scheduler (%date%)" >> logs.txt 2>&1
git push origin main >> logs.txt 2>&1

echo Finished update run at %date% %time% >> logs.txt
echo ================================================== >> logs.txt

