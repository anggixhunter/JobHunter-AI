@echo off
TITLE Job Hunter AI - Automation System

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    goto run
)
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    goto run
)
if exist "..\Scripts\activate.bat" (
    call "..\Scripts\activate.bat"
    goto run
)
if exist "..\..\Scripts\activate.bat" (
    call "..\..\Scripts\activate.bat"
    goto run
)

echo [!] venv tidak ditemukan.
echo     Buat dulu:
echo         python -m venv venv
echo         venv\Scripts\activate
echo         pip install -r requirements.txt
echo.
pause
exit /b 1

:run
python TesAPI.py
pause
