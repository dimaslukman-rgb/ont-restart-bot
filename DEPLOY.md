# Deploy ke Railway.app 🚂

Panduan deploy ONT Restart Bot ke Railway.app biar jalan 24/7 tanpa harus nyala-in laptop terus.

## Honest assessment dulu

**Bisa ga?**: Bisa. **Mepet ga?**: Agak.

| Komponen | Estimasi | Railway Free Tier |
|---|---|---|
| Image base (Playwright + Chromium) | ~600 MB | OK (ephemeral disk 1+ GB) |
| Memory per container | ~250-400 MB pas lagi restart | Default 512 MB free — pas-pasan |
| CPU | Burst pas lagi restart | OK |
| Runtime | 24/7 = 720 jam/bulan | $5 credit ≈ 500 jam |
| Ephemeral disk | Hilang tiap redeploy | Pakai Volume kalo perlu persistent |

**Verdict**: Gratis *cukup* kalo bot dipake jarang (beberapa kali seminggu, biar hemat credit). Kalo dipake setiap hari atau beberapa kali sehari, **Hobby plan $5/bulan flat** lebih tenang — dapet 8 GB RAM, no metering.

---

## Step 1: Push ke GitHub

```bash
cd ont-restart-bot
git init
git add .
git commit -m "Initial commit: ONT restart bot"
# Bikin repo baru di github.com, trus:
git remote add origin git@github.com:USERNAME/ont-restart-bot.git
git branch -M main
git push -u origin main
```

> **JANGAN** push file `.env` ke GitHub — itu ada password & token-nya. `.gitignore` udah exclude, tapi tetep double-check.

## Step 2: Connect ke Railway

1. Buka https://railway.app → login (recommended via GitHub)
2. Klik **New Project** → **Deploy from GitHub repo**
3. Pilih repo `ont-restart-bot`
4. Railway bakal auto-detect `Dockerfile` di root → build image

## Step 3: Set Environment Variables

Di Railway dashboard → service kamu → tab **Variables**, tambahin satu-satu:

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `8949804444:AAErz4aQGMfcRlmG3Ndg6ifZpvYlTthMC10` |
| `TELEGRAM_ALLOWED_USERS` | Telegram user ID Pak Boss (chat `/myid` di bot lokal dulu buat tau) |
| `ACSIS_BASE_URL` | `https://acs-ibooster.telkom.co.id` |
| `ACSIS_USERNAME` | `16871006` |
| `ACSIS_PASSWORD` | password ACSIS Pak Boss |
| `ACSIS_LOGIN_OPTION` | `Telkom Akses` |
| `ACSIS_TOTP_SECRET` | `FFXGO3CRPIZGYWTYJBXTM53QFJISIOLXIM3VCKRIHZ2FIPDXHBSQ` |
| `LOG_LEVEL` | `INFO` |
| `ACSIS_HEADLESS` | `true` |
| `DEBUG_SCREENSHOT_DIR` | kosongkan (gak kepake di production) |

> ⚠️ Pak Boss tetep harus jalanin bot lokal **sekali aja** buat dapet Telegram user ID via `/myid`. Bisa juga pake @userinfobot di Telegram (kirim chat apa aja, dia reply user ID).

## Step 4: Set Service Type jadi Worker

Bot ini bukan web server (gak expose HTTP port). Jadi:

1. Di Railway dashboard → service → **Settings**
2. **Deploy** section → **Custom Start Command**: `python -u bot.py`
3. **Service** type: cari di Settings → harus `worker` (atau uncheck "HTTP Service")

> Di Railway baru, semua service auto-detect. Kalo bot jalan terus tanpa error, dia udah jadi worker. Kalo Railway complain soal "port not exposed", tinggal masukin dummy port env.

## Step 5: Deploy & Verify

1. Klik **Deploy** (atau auto-deploy dari push ke main)
2. Tab **Deployments** → liat build logs
3. Tab **Logs** → harusnya muncul `Bot starting. Allowed users: [...]`
4. Buka Telegram → chat bot kamu → `/start`
5. Test `/restart <no_internet>`

## Step 6 (opsional): Custom Domain / URL

Kalo mau akses HTTP endpoint (misal healthcheck), bisa:
- Tambahin variabel `PORT=8080`
- Di `bot.py`, tambahin tiny HTTP server di background

Tapi buat sekarang gak perlu — bot Telegram pure TCP polling.

---

## Troubleshooting Railway

### Build gagal: "no space left on device"
- Image Playwright + Chromium = ~600 MB, build context tambahin
- Fix: tambahin `.dockerignore` (sudah ada) atau upgrade ke Hobby plan

### Container restart terus
- Cek tab **Logs** — biasanya `KeyError: 'ACSIS_PASSWORD'` kalo env var lupa
- Atau `TELEGRAM_BOT_TOKEN invalid` kalo token salah

### Bot gak respond di Telegram
- Cek logs → ada tulisan "Bot starting" gak?
- Kalo ada, masalahnya network egress (Railway block ke `acs-ibooster.telkom.co.id`?). Hubungi support.

### Credit cepat habis
- Normal kalo free tier + 24/7. Bot idle tetep makan credit dikit.
- Solusi: upgrade Hobby $5/bulan, atau jalanin di VPS murah lain.

### TOTP_INVALID padahal secret udah bener
- Clock drift di container Railway. Fix: set env var `TZ=Asia/Jakarta` di Railway Variables.

---

## Alternatif selain Railway

Kalo Railway berasa ribet, ini komparasi:

| Platform | Biaya | Pros | Cons |
|---|---|---|---|
| **Fly.io** | Free tier 3 shared VMs | Cold start-friendly, ada region Asia (Singapore) | Setup CLI lebih ribet dari Railway |
| **Render** | Free tier (ada cold start) | Simpel kayak Railway | Cold start ~30 detik, ganjel banget buat bot |
| **Contabo VPS** | $4.34/bulan (4GB RAM) | Spek gede, hemat | Setup manual (ssh, systemd) |
| **Oracle Cloud Free Tier** | $0 selamanya | 4 CPU, 24 GB RAM | Apply susah, approval lama |
| **Hostinger VPS** | Rp 80-100rb/bulan | Support bahasa Indo | Spek pas-pasan di tier termurah |

Buat kasus ini, Momo pribadi akan pilih **Contabo VPS $4.34/bulan** atau **Fly.io free tier** dibanding Railway, karena Playwright butuh resource predictable. Tapi Railway tetep oke kalo Pak Boss mau yang "click and deploy" paling cepet.
