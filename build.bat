@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python nie jest zainstalowany.
  echo Instalowanie Python 3.12 przez winget...
  winget install --id Python.Python.3.12 -e --source winget
  if errorlevel 1 (
    echo Nie udalo sie zainstalowac Pythona. Zainstaluj Python 3.12 i uruchom ponownie.
    pause
    exit /b 1
  )
)
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --onefile --windowed --name MouseSyncDelay mouse_sync_delay.py
echo.
echo GOTOWE: dist\MouseSyncDelay.exe
pause
