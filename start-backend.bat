@echo off
echo ==========================================
echo  ThinkPadLLM - Starting Backend (Flask)
echo ==========================================
cd /d "%~dp0\backend"
call venv\Scripts\activate
python run.py
pause
