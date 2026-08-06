@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  install_task.bat - daftarkan bot ke Windows Task Scheduler
rem  (butuh admin? Gak - schtasks /Create biasa cukup)
rem  - Task "ONT Restart Bot": jalan otomatis saat user login
rem  - Task "ONT Restart Bot Health": watchdog tiap 5 menit
rem ============================================================

echo Mendaftarkan task "ONT Restart Bot" (jalan saat login)...
schtasks /Create /F /TN "ONT Restart Bot" /TR "\"%~dp0start_bot.bat\"" /SC ONLOGON /RL LIMITED

echo Mendaftarkan task "ONT Restart Bot Health" (tiap 5 menit)...
schtasks /Create /F /TN "ONT Restart Bot Health" /TR "\"%~dp0healthcheck.bat\"" /SC MINUTE /MO 5 /RL LIMITED

echo.
echo Selesai! Cek:  Win+R  ->  taskschd.msc
echo Task "ONT Restart Bot" bakal jalan otomatis tiap kali kamu login Windows.
echo Kalau mau cek langsung tanpa login ulang, jalankan start_bot.bat manual.
