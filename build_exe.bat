@echo off
title HeadRush NAM Studio - Builder
echo =======================================================
echo  Building HeadRush NAM Studio Standalone Executable
echo =======================================================
echo.

python -m venv .venv
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Building single-file executable with PyInstaller...
pyinstaller --noconsole --onefile --name "HeadRush_NAM_Studio" --collect-all customtkinter --distpath dist main.py --clean -y

echo.
echo =======================================================
echo  BUILD COMPLETE! Executable located in: dist\HeadRush_NAM_Studio.exe
echo =======================================================
pause
