@echo off
setlocal EnableExtensions

rem ============================================================
rem  uninstall_task.bat - berhentiin bot + hapus semua task
rem ============================================================

echo Menghentikan proses bot yang sedang jalan...
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo Menghapus task scheduler...
schtasks /Delete /F /TN "ONT Restart Bot"
schtasks /Delete /F /TN "ONT Restart Bot Health"

echo Menghapus shortcut Startup (kalau ada)...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ONT Restart Bot.lnk" >nul 2>&1

echo.
echo Selesai. Kalau window "ONT Restart Bot" masih kebuka, tutup manual.
