@echo off
setlocal EnableExtensions

rem ============================================================
rem  start_bot.bat - jalankan bot 24/7 dengan auto-restart
rem  - Guard: kalau bot.py udah jalan, script ini langsung keluar
rem  - Loop: kalau bot mati/crash, tunggu 5 detik lalu jalanin lagi
rem  - Log: semua output ditulis ke bot.log (otomatis rotate 5 MB)
rem  Dipanggil oleh Task Scheduler / Startup folder / manual.
rem ============================================================

rem Self-minimize: kalau dipanggil tanpa argumen, buka ulang
rem di window kecil berjudul "ONT Restart Bot".
if not "%~1"=="loop" (
    start "ONT Restart Bot" /min cmd /c ""%~f0" loop"
    exit /b
)

cd /d "%~dp0"
title ONT Restart Bot

rem ---- Guard: kalau ada python bot.py yang jalan, skip ----
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'bot\.py' }; if ($p) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [%date% %time%] Bot udah jalan, skip.
    exit /b 0
)

echo [%date% %time%] ============================================
echo [%date% %time%]  ONT Restart Bot dimulai...
echo [%date% %time%]  Log: bot.log  |  Heartbeat: bot_heartbeat.txt
echo [%date% %time%] ============================================

:loop

rem ---- Rotate log kalau udah > 5 MB ----
for %%F in (bot.log) do if %%~zF GTR 5242880 (
    move /y bot.log bot.log.old >nul 2>&1
    echo [%date% %time%] bot.log di-rotate ke bot.log.old
)

echo [%date% %time%] Menjalankan bot.py...
py -3 -u bot.py >> bot.log 2>&1
set "CODE=%ERRORLEVEL%"

echo [%date% %time%] Bot berhenti (exit code %CODE%). Restart dalam 5 detik...
timeout /t 5 /nobreak >nul
goto loop
