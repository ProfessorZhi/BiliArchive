@echo off
setlocal

cd /d "%~dp0\..\.."
python -m PyInstaller --noconfirm --clean tools\packaging\BiliArchive.spec

echo.
echo Build finished.
echo EXE path: %CD%\dist\BiliArchive.exe

endlocal
