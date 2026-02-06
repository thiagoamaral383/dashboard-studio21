@echo off
echo --- Studio21 Data Extractor ---
echo.
python src/main.py
echo.
if %errorlevel% neq 0 (
    echo [ERROR] The script encountered an issue. Please check the logs above.
) else (
    echo [SUCCESS] Extraction completed successfully.
)
pause
