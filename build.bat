@echo off
echo Building 5StarBookKeeping...
echo.

pip install pyinstaller --quiet

pyinstaller build.spec --clean --noconfirm

echo.
echo Build complete! Executable is in: dist\5StarBookKeeping.exe
pause
