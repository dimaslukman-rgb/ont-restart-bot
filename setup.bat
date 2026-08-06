@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  setup.bat - setup sekali jalan buat bot 24/7 di PC ini
rem  1. Install dependency + Chromium (pakai py launcher)
rem  2. Buat .env dari .env.example kalau belum ada
rem  3. Verifikasi DNS ACSIS (WAJIB resolve dari jaringan ini!)
rem  4. Daftarkan Task Scheduler (auto-start + watchdog)
rem  5. Jalanin bot-nya
rem ============================================================

echo ============================================================
echo   ONT Restart Bot - Setup 24/7 (Windows)
echo ============================================================
echo.

rem ---- 1. Dependency ----
echo [1/5] Install dependency Python...
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
echo [1/5] Download Chromium buat Playwright (sekitar 150 MB, sekali doang)...
py -3 -m playwright install chromium
echo.

rem ---- 2. .env ----
echo [2/5] Cek file .env...
if exist ".env" (
    echo .env sudah ada - dipakai apa adanya.
) else (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo .env baru dibuat dari .env.example.
        echo.
        echo   *** PENTING: EDIT .env DULU - isi TELEGRAM_BOT_TOKEN, ***
        echo   *** ACSIS_USERNAME/PASSWORD/TOTP_SECRET, dst.        ***
        echo.
    ) else (
        echo ERROR: .env.example gak ketemu - gak bisa lanjut.
        pause
        exit /b 1
    )
)
echo.

rem ---- 3. Verifikasi DNS ----
echo [3/5] Verifikasi DNS ACSIS (harus resolve dari jaringan Telkom ini)...
py -3 -c "import socket; ip = socket.gethostbyname('acs-ibooster.telkom.co.id'); print('  OK: acs-ibooster.telkom.co.id ->', ip)"
if errorlevel 1 (
    echo.
    echo   *** PERINGATAN: domain ACSIS GAGAL resolve dari jaringan ini. ***
    echo   *** Bot gak bakal bisa login. Pastikan PC ini di jaringan   ***
    echo   *** Telkom/IndiHome, bukan VPN/cloud publik.                 ***
    echo.
)
echo.

rem ---- 4. Task Scheduler ----
echo [4/5] Daftarkan auto-start + watchdog ke Task Scheduler...
call install_task.bat
echo.

rem ---- 5. Jalankan bot ----
echo [5/5] Menjalankan bot sekarang...
start "" /min "%~dp0start_bot.bat"
echo.
echo Setup selesai! Bot jalan di window "ONT Restart Bot".
echo Cek status: kirim /start ke bot kamu di Telegram.
echo Log: bot.log   ^|   Health check: healthcheck.bat (tiap 5 menit via task).
echo.
pause
