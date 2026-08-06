# Bot 24/7 di PC Windows

> **Kenapa di PC?** `acs-ibooster.telkom.co.id` cuma bisa diakses dari **dalam jaringan Telkom** (DNS internal, IP privat `10.x`). Cloud publik seperti Railway/Hetzner/Kamatera **mustahil** reach domain ini. Jadi bot harus jalan dari PC kamu (jaringan IndiHome/Telkom). Kabar baiknya: Telegram bot pakai **long polling** (koneksi keluar aja), jadi **tidak perlu port forwarding** — cukup PC nyala.

> **⚠️ PAUSE RAILWAY DULU!** Selama bot masih jalan di Railway, bot lokal kamu gak bisa polling — Telegram cuma ngizinin **satu** consumer `getUpdates` per token, dan yang lain bakal kena `Conflict: terminated by other getUpdates request`. Jadi sebelum nyalain bot di PC: buka Railway → pilih service → **Pause/Stop**, atau hapus deployment-nya.

---

## Ringkasan arsitektur

```
Task Scheduler (saat login)         Task Scheduler (tiap 5 menit)
        │                                   │
        ▼                                   ▼
  start_bot.bat ◄────────────────  healthcheck.bat (watchdog)
        │                                   │
        ▼                                   ▼
   loop: py -3 -u bot.py          cek bot_heartbeat.txt (fresh ≤ 180 dtk?)
        │   ▲                     kalau basi → bunuh bot → wrapper restart
        └───┘ auto-restart 5 dtk
```

- **`bot.py`** menulis `bot_heartbeat.txt` setiap 60 detik (sudah ditambahkan).
- **`start_bot.bat`** = wrapper: guard anti-duplikat + loop auto-restart + log ke `bot.log` (rotate otomatis 5 MB).
- **`healthcheck.bat`** = watchdog: kalau heartbeat basi (bot hang/mati), bunuh prosesnya — wrapper bakal nyalain ulang. Kalau wrapper-nya mati juga, dia nyalain ulang semuanya.

---

## Setup sekali jalan

1. **Clone / taruh folder project** di PC, contoh: `C:\Users\ASUS\Documents\Codex\ont-restart-bot`.
2. **Isi `.env`** — kalau belum ada, copy dari `.env.example`:
   ```bash
   copy .env.example .env
   ```
   Lalu edit `.env` — semua variabel wajib ada keterangannya di dalam file itu.
3. **Jalankan `setup.bat`** (klik 2x). Ini otomatis:
   - install dependency ke interpreter `py`
   - download Chromium buat Playwright
   - verifikasi DNS ACSIS (harus resolve dari jaringan ini!)
   - daftarkan Task Scheduler
   - nyalain bot
4. **Tes**: buka Telegram → kirim `/start` → kirim `/restart <no_internet>`.

> Kalau mau manual tanpa `setup.bat`:
> ```bash
> py -3 -m pip install -r requirements.txt
> py -3 -m playwright install chromium
> start_bot.bat
> ```

---

## Panduan `.env` lengkap

| Variabel | Wajib? | Isi |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token dari @BotFather |
| `TELEGRAM_ALLOWED_USERS` | ⚠️ | User ID yang boleh pakai (spasi-separated). Kosongkan = semua orang bisa! |
| `ACSIS_USERNAME` | ✅ | Username login ACSIS |
| `ACSIS_PASSWORD` | ✅ | Password login ACSIS |
| `ACSIS_LOGIN_OPTION` | | Opsi dropdown role, default `Telkom Akses` |
| `ACSIS_TOTP_SECRET` | ✅ | Secret TOTP (tanpa spasi/`=`) dari Google Authenticator |
| `ACSIS_BASE_URL` | | Default `https://acs-ibooster.telkom.co.id` |
| `ACSIS_HEADLESS` | | `true` (default) / `false` buat liat browser saat debug |
| `LOG_LEVEL` | | `INFO` (default) / `DEBUG` |
| `DEBUG_SCREENSHOT_DIR` | | Folder screenshot tiap step (opsional), contoh `./screenshots` |

Cara dapetin ulang TOTP secret:
1. Google Authenticator → ⋮ → **Export accounts** → scan QR akun ACSIS
2. Dapet string `otpauth-migration://offline?data=...`
3. Decode (script `decode_totp.py` di repo ini, atau online di devtool.tech) → ambil bagian **Secret** → paste ke `ACSIS_TOTP_SECRET`

---

## Auto-start (dua pilihan)

**Opsi A — Task Scheduler (disarankan, ada watchdog):**
```bash
install_task.bat
```
Mendaftarkan:
- `ONT Restart Bot` — jalan saat user login
- `ONT Restart Bot Health` — watchdog tiap 5 menit

> 💡 **Tanpa admin?** Task `ONLOGON` butuh hak admin. Kalau `install_task.bat` ditolak ("Access is denied"), dia **otomatis fallback ke Startup folder** buat auto-start — watchdog `Health` (tiap 5 menit, tanpa admin) tetap terdaftar. Jadi kombinasi final: Startup shortcut (auto-start saat login) + Task Scheduler (watchdog).

**Opsi B — Startup folder (manual, tanpa admin, tanpa watchdog):**
```bash
install_startup.bat
```
Bikin shortcut minimized di Startup folder. Bot auto-start saat login, crash-restart tetap jalan (lewat loop `start_bot.bat`), tapi watchdog tiap 5 menit tidak aktif (kecuali kamu jalanin `install_task.bat` juga buat task Health-nya).

**Hapus semuanya:**
```bash
uninstall_task.bat
```

---

## Operasional harian

| Aksi | Cara |
|---|---|
| Lihat log | `bot.log` (folder project). Rotate otomatis ke `bot.log.old` kalau > 5 MB |
| Cek bot hidup | File `bot_heartbeat.txt` — kalau mtime-nya < 3 menit, bot sehat |
| Health check manual | `healthcheck.bat` |
| Stop bot | `uninstall_task.bat`, atau tutup window "ONT Restart Bot" |
| Ganti kredensial | Edit `.env` → jalankan `start_bot.bat` lagi (guard: kalau bot masih jalan, tutup dulu window-nya / `uninstall_task.bat`) |

### Biar PC gak tidur (opsional, butuh admin)
```bash
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
```
Jalankan di **Command Prompt sebagai Administrator**. Balikin ke normal: ganti `0` dengan menit yang diinginkan, atau lewat Settings → System → Power & sleep.

### Troubleshooting

| Gejala | Cek |
|---|---|
| Bot gak balas | `bot_heartbeat.txt` ada? Kalau basi terus dan `healthcheck.bat` sering restart, lihat `bot.log` |
| `net::ERR_NAME_NOT_RESOLVED` | PC bukan di jaringan Telkom. Jalankan `py -3 -c "import socket; print(socket.gethostbyname('acs-ibooster.telkom.co.id'))"` — harus keluar IP, bukan error |
| `playwright` executable gak ketemu | `py -3 -m playwright install chromium` |
| `py` gak ketemu | Install Python dari python.org, centang "Add python.exe to PATH" |
