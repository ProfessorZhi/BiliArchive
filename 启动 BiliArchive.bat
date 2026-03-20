@echo off
setlocal

cd /d "%~dp0"
if exist local_env.bat call local_env.bat

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
  "$procs = Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'pythonw.exe' -or $_.Name -ieq 'python.exe') -and $_.CommandLine -like '*src\\gui_qt.py*' }; $procs | ForEach-Object { $_.ProcessId }"`) do (
    taskkill /PID %%i /F >nul 2>nul
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw src\gui_qt.py
) else (
    start "" python src\gui_qt.py
)

endlocal
