@echo off
setlocal

REM =========================================================
REM Build AudioTestLogAnalyzer.exe
REM Run this from inside the exe_project folder
REM =========================================================

echo.
echo ========================================
echo   Audio Test Log Analyzer EXE Builder
echo ========================================
echo.

REM ---------------------------------------------------------
REM Check if Python is installed
REM ---------------------------------------------------------

echo Checking Python...

py --version >nul 2>&1

if errorlevel 1 (
echo.
echo ERROR: Python was not found.
echo.
echo Please install Python and make sure the Python
echo Launcher is installed.
echo.
pause
exit /b 1
)

echo Python found.
py --version

REM ---------------------------------------------------------
REM Install dependencies
REM ---------------------------------------------------------

echo.
echo Installing dependencies...

py -m pip install --upgrade pip

if errorlevel 1 (
echo.
echo ERROR: Failed to update pip.
pause
exit /b 1
)

py -m pip install -r requirements.txt

if errorlevel 1 (
echo.
echo ERROR: Failed to install requirements.
echo.
pause
exit /b 1
)

REM ---------------------------------------------------------
REM Install / verify PyInstaller
REM ---------------------------------------------------------

echo.
echo Installing PyInstaller...

py -m pip install pyinstaller

if errorlevel 1 (
echo.
echo ERROR: Failed to install PyInstaller.
echo.
pause
exit /b 1
)

REM ---------------------------------------------------------
REM Build EXE
REM ---------------------------------------------------------

echo.
echo Building EXE...

if not exist "app.ico" (
echo.
echo ERROR: app.ico was not found in this folder.
echo.
echo Place your icon file ^(named app.ico^) next to app.py
echo before building.
echo.
pause
exit /b 1
)

py -m PyInstaller --noconfirm --clean --onefile --windowed ^
--icon "app.ico" ^
--add-data "index.html;." ^
--add-data "lib;lib" ^
--add-data "app.ico;." ^
--collect-all py7zr ^
--name "AudioTestLogAnalyzer" ^
app.py

if errorlevel 1 (
echo.
echo ========================================
echo BUILD FAILED
echo ========================================
echo.
echo Check the error messages above.
echo.
pause
exit /b 1
)

REM ---------------------------------------------------------
REM Verify EXE exists
REM ---------------------------------------------------------

if not exist "dist\AudioTestLogAnalyzer.exe" (
echo.
echo ERROR: Build finished but EXE was not found.
echo.
pause
exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Your EXE is located at:
echo.
echo %CD%\dist\AudioTestLogAnalyzer.exe
echo.

pause
