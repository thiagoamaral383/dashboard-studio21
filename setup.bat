@echo off
echo --- Studio21 Setup ---
echo Creating/Activating virtual environment...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing required Python libraries...
echo.
pip install -r requirements.txt
echo.
echo Setup completed! You can now use run.bat to start the extractor.
pause
