# ONT Restart Telegram Bot 🤖🔌

Bot Telegram buat restart ONT pelanggan via situs **ACSIS ibooster Telkom**.
Bot ini nge-drive Playwright (headless Chromium) buat login → OTP (TOTP) → search → restart, semua dari chat Telegram.

---

## Flow

1. **Login** ke `https://acs-ibooster.telkom.co.id/login`
2. **OTP** di-generate sendiri dari TOTP secret (Google Authenticator)
3. **Cari** No Internet di halaman `/home`
4. **Klik** menu "Restart ONT" di sidebar
5. **Auto-accept** dialog konfirmasi & dialog hasil
6. **Lapor** hasilnya balik ke Telegram

---

## Setup

### 1. Install dependency
```bash
cd ont-restart-bot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Konfigurasi `.env`
Copy `.env.example` ke `.env`, lalu isi:

| Variable | Isi |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token dari `@BotFather` (sudah diisi) |
| `TELEGRAM_ALLOWED_USERS` | User ID Telegram yang boleh pake (spasi-separated). Pakai `/myid` di bot buat tau ID kamu. |
| `ACSIS_USERNAME` | Username ACSIS (sudah terisi: `16871006`) |
| `ACSIS_PASSWORD` | **Wajib diisi** — password login ACSIS |
| `ACSIS_LOGIN_OPTION` | Sudah `Telkom Akses` |
| `ACSIS_TOTP_SECRET` | Sudah terisi hasil decode dari QR Google Authenticator |
| `DEBUG_SCREENSHOT_DIR` | (Opsional) Path folder buat simpan screenshot debug tiap step |

### 3. Cara dapetin TOTP secret (kalau perlu reset)
1. Buka Google Authenticator → klik ⋮ → **Export accounts** → scan QR akun ACSIS
2. Hasilnya string `otpauth-migration://offline?data=...`
3. Decode pakai script kecil, atau online di [devtool.tech](https://devtool.tech/google-authenticator-qrcode) — extract bagian "Secret"
4. Paste ke `ACSIS_TOTP_SECRET`

### 4. Jalanin
```bash
python bot.py
```

Bot langsung polling. Coba chat `/start` di Telegram.

---

## Cara pakai di Telegram

```
/myid                    # cek user ID kamu
/restart 122868308296    # restart ONT no internet 122868308296
```

Bot bakal kirim status update dari "⏳ mulai" → "✅ Berhasil" / "❌ Gagal".

---

## Struktur project

```
ont-restart-bot/
├── .env.example        # template env
├── .gitignore
├── automation.py       # Playwright automation (login → OTP → restart)
├── bot.py              # Telegram bot (command handler)
├── requirements.txt
└── README.md
```

---

## Catatan teknis

- **Headless Chromium**: bot jalan di background, gak ada window browser. Set `ACSIS_HEADLESS=false` di `.env` kalau mau liat browsernya (debug).
- **OTP 6-digit**: generator TOTP pakai `pyotp` + secret base32 dari Google Authenticator.
- **Tiap restart = sesi baru**: gak ada caching session, jadi lebih aman kalo TOTP-nya expire.
- **Lock per chat**: 1 chat cuma bisa jalanin 1 restart sekaligus, biar gak tabrakan.
- **Timeout**: Step login/OTP maks 15 detik; total flow maks ~60 detik.

---

## Troubleshooting

| Gejala | Likely cause |
|---|---|
| "Gagal masuk ke halaman OTP" | Username/password salah, atau dropdown TelAkses gak ke-pilih |
| "OTP kemungkinan salah" | TOTP secret di `.env` beda sama yang di Google Authenticator |
| "Fiber info tidak muncul" | No Internet salah / tidak ada di sistem |
| "Tidak menerima pop-up hasil" | Struktur web berubah, atau restart emang gagal di sisi server |
| Bot gak respond | Cek token `TELEGRAM_BOT_TOKEN`; cek firewall server |

Kalo ada masalah, set `DEBUG_SCREENSHOT_DIR=./screenshots` di `.env` biar bot nyimpen screenshot tiap step. Cek file `final.png` dan `*.png` lain di folder itu.

---

## Deploy 24/7

Lihat **[DEPLOY.md](DEPLOY.md)** untuk step-by-step deploy ke Railway.app (Dockerfile-based), plus komparasi platform lain (Fly.io, Render, Contabo, Oracle Cloud Free Tier).

Quick deploy ke Railway:
1. Push repo ke GitHub
2. `https://railway.app` → New Project → Deploy from GitHub
3. Set environment variables (lihat DEPLOY.md)
4. Service type: **worker** (bot bukan web server)
5. Deploy → tunggu logs `Bot starting...`
