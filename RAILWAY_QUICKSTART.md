# Railway Quickstart 🚂

5 langkah deploy ONT Restart Bot ke Railway.app. Paling simpel.

---

## Step 0: Push code ke GitHub (di laptop)

```powershell
cd "C:\Users\ASUS\WorkBuddy AI\Claw\ont-restart-bot"
git init
git add .
git commit -m "init"
```

Bikin repo baru di https://github.com/new (jangan centang README, .gitignore, license — biar kosong).

Balik ke terminal:
```powershell
git remote add origin https://github.com/USERNAME/ont-restart-bot.git
git branch -M main
git push -u origin main
```

> ⚠️ JANGAN push file `.env` — file `.gitignore` udah exclude, tapi double-check.

---

## Step 1: Login Railway

1. Buka https://railway.app
2. Klik **Login** → **Login with GitHub**
3. Authorize Railway ke akun GitHub lo

---

## Step 2: Deploy dari GitHub

1. Klik **New Project**
2. Pilih **Deploy from GitHub repo**
3. Pilih repo `ont-restart-bot`
4. Railway auto-detect **Dockerfile** → mulai build

Build pertama ~3-5 menit (download base image Playwright ~600 MB).

---

## Step 3: Set Environment Variables

Di Railway dashboard → service kamu → tab **Variables** → klik **+ New Variable** satu-satu:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `8949804444:AAErz4aQGMfcRlmG3Ndg6ifZpvYlTthMC10` |
| `TELEGRAM_ALLOWED_USERS` | *(user ID Telegram, lihat catatan di bawah)* |
| `ACSIS_BASE_URL` | `https://acs-ibooster.telkom.co.id` |
| `ACSIS_USERNAME` | `16871006` |
| `ACSIS_PASSWORD` | *(password ACSIS asli — WAJIB ISI)* |
| `ACSIS_LOGIN_OPTION` | `Telkom Akses` |
| `ACSIS_TOTP_SECRET` | `FFXGO3CRPIZGYWTYJBXTM53QFJISIOLXIM3VCKRIHZ2FIPDXHBSQ` |
| `TZ` | `Asia/Jakarta` |
| `LOG_LEVEL` | `INFO` |

> **Cara dapet TELEGRAM_ALLOWED_USERS**:
> 1. Jalanin bot di lokal (`python bot.py`)
> 2. Chat `/myid` di Telegram → bot reply user ID
> 3. Paste ID itu (contoh: `123456789`)

---

## Step 4: Verifikasi Deploy

1. Tab **Deployments** → liat build & deploy log
2. Tab **Logs** → harusnya ada:
   ```
   INFO Bot starting. Allowed users: [123456789]
   ```
3. **Kalo gak ada log / error "KeyError"** → cek env var (kemungkinan `ACSIS_PASSWORD` lupa)
4. **Kalo ada error laen** → copy paste error ke Momo

---

## Step 5: Test di Telegram

1. Buka Telegram
2. Cari bot lo (username yang dibikin di @BotFather)
3. Chat `/start` → harusnya reply menu
4. Test `/restart 122868308296` → tunggu 15-60 detik

✅ Beres — bot 24/7!

---

## Maintenance

| Task | Caranya |
|---|---|
| Liat log | Railway dashboard → Logs tab |
| Restart service | Settings → klik "Restart" |
| Update code | `git push` dari laptop → auto-deploy |
| Tambah env var | Variables tab → + New Variable |

---

## Honest notes soal $5 credit Railway

- **Free tier**: $5 credit/bulan (rolling)
- **Bot idle**: makan ~$0.01-0.05/hari = $0.30-1.5/bulan
- **Bot pas restart**: makan ~$0.001 per restart (15-60 detik)
- **Verdict**: Gratis **cukup** untuk penggunaan normal (beberapa restart/hari)
- **Kalo credit abis**: upgrade ke **Hobby plan $5/bulan** (flat, no metering)

Cara cek sisa credit: Railway dashboard → klik nama lo (kanan atas) → "Plan & Usage".

---

## Troubleshooting

| Gejala | Fix |
|---|---|
| Build fail: "no space left" | Image Playwright gede. Tungguin auto-retry, atau upgrade plan |
| Container restart terus | Cek Logs. Biasanya `KeyError: 'ACSIS_PASSWORD'` |
| Bot start tapi gak respond | Cek Logs ada "Bot starting" gak. Kalo ada, masalah network atau TELEGRAM_ALLOWED_USERS salah |
| TOTP invalid | Pastiin `TZ=Asia/Jakarta` ada di env vars |
| Port error | Tambahin env var `PORT=8080` (biarin aja gak dipake) |

---

## 💡 Tips upgrade kalo butuh 24/7 reliable

Kalo Pak Boss ngerasa Railway free tier terlalu riskan (mungkin credit abis di tengah malam), Momo bisa bikinkan auto-alert ke Telegram kalau bot-nya mati. Tapi itu nanti aja kalo perlu.
