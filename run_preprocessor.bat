@echo off
REM ============================================
REM Financial Data Preprocessor
REM Parses Excel files from Google Drive and creates CSV files
REM ============================================

echo ============================================
echo Financial Data Preprocessor
echo ============================================
echo.

REM Check if G: drive exists
if exist G:\ (
    echo G: drive found - using local Google Drive
    set DATA_SOURCE=G:\My Drive\Ai Chatbot Knowledge Base
) else (
    echo G: drive NOT found!
    echo Please make sure Google Drive is mounted as G:
    pause
    exit /b 1
)

echo Data source: %DATA_SOURCE%
echo.

REM Change to workspace directory
cd /d "%~dp0"

echo Running preprocessor...
echo.

REM Run the preprocessor
python financial_preprocessor.py %DATA_SOURCE%

echo.
if %ERRORLEVEL% == 0 (
    echo ============================================
    echo SUCCESS! Data has been processed.
    echo.
    echo Files are saved in:
    echo %DATA_SOURCE%\2025\XX\xxx_flat.csv
    echo.
    echo The chatbot will use these files automatically.
    echo ============================================
) else (
    echo ERROR! Preprocessing failed.
    echo Check the error messages above.
)

pause
