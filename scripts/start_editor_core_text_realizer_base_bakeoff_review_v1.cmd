@echo off
cd /d "%~dp0.."
python src\pastila_scout\editor_base_bakeoff_review_app.py --pack .editor-base-bakeoff-review-v1-car3\pack.json --state .editor-base-bakeoff-review-v1-car3\scores
