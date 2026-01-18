@echo off
echo Installing requirements...
pip install -r requirements.txt

echo Building MasterDownloader...
pyinstaller --noconfirm --onedir --windowed --name "MasterDownloader" --add-data "gui_config.json;." --add-data "history.json;." --add-data "ig_credentials.txt;." --add-data "manual_cookie.txt;." --add-data "sessions;sessions" App.py

echo Build complete!
echo You can find the application in dist\MasterDownloader\MasterDownloader.exe
pause
