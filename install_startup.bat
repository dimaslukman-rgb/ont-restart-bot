@echo off
setlocal EnableExtensions

rem ============================================================
rem  install_startup.bat - ALTERNATIF tanpa Task Scheduler
rem  Bikin shortcut "ONT Restart Bot" di Startup folder (tanpa admin).
rem  Bot otomatis jalan tiap login, tanpa perlu izin admin.
rem  Catatan: tanpa Task Scheduler, watchdog healthcheck.bat TIDAK
rem  dijadwalkan - tapi start_bot.bat tetap auto-restart kalau crash.
rem ============================================================

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP%\ONT Restart Bot.lnk'); $s.TargetPath = '%~dp0start_bot.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Save()"

echo Shortcut dibuat di: %STARTUP%
echo Bot bakal jalan otomatis tiap kali kamu login.
echo (Catatan: pake Task Scheduler lebih lengkap - lihat install_task.bat)
