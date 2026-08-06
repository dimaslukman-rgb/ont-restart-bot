@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  healthcheck.bat - watchdog otomatis (jalan tiap 5 menit)
rem  Cek file bot_heartbeat.txt yang ditulis bot.py tiap 60 detik:
rem    - Heartbeat fresh  -> bot sehat, keluar
rem    - Heartbeat basi   -> bot hang/mati: bunuh prosesnya, dan
rem      start_bot.bat (kalau masih hidup) bakal restart otomatis.
rem      Kalau wrapper-nya mati juga, script ini nyalain ulang.
rem ============================================================

set "HB=%~dp0bot_heartbeat.txt"

:check
powershell -NoProfile -Command ^
  "$f='%HB%'; if (!(Test-Path $f)) { exit 1 }; $a=(Get-Date)-(Get-Item $f).LastWriteTime; if ($a.TotalSeconds -gt 180) { exit 1 } else { exit 0 }"
if not errorlevel 1 (
    exit /b 0
)

echo [%date% %time%] Heartbeat basi / gak ada - bot hang atau mati.

rem ---- Bunuh proses bot lama (wrapper bakal restart dalam 5 detik) ----
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

rem ---- Tunggu, lalu cek lagi: kalau masih basi, wrapper-nya mati juga ----
timeout /t 6 /nobreak >nul

powershell -NoProfile -Command ^
  "$f='%HB%'; if (!(Test-Path $f)) { exit 1 }; $a=(Get-Date)-(Get-Item $f).LastWriteTime; if ($a.TotalSeconds -gt 180) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [%date% %time%] Wrapper mati juga - mulai ulang start_bot.bat.
    start "" /min "%~dp0start_bot.bat"
) else (
    echo [%date% %time%] Bot berhasil di-restart oleh wrapper.
)

exit /b 0
