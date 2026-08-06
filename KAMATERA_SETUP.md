# Deploy ke Kamatera Cloud ☁️

Panduan lengkap dari **0 (form Kamatera)** sampai bot jalan 24/7 di VPS.

## Kenapa Kamatera oke buat bot ini

| Aspek | Detail |
|---|---|
| Region Asia | Singapore (deket Indonesia, latency ~30ms ke Jakarta) |
| Spec minimum | 1 CPU, 1 GB RAM, 20 GB SSD — cukup buat bot ini |
| Harga | ~$4/bulan (type A1 entry) — cheaper dari Railway Hobby |
| Tanpa cold start | Bot langsung nyala, gak ada delay pas dipake |
| Billing fleksibel | Monthly cycle, gak ada commitment |
| SSH langsung | Akses root dari awal, gak ada UI ribet |

Cocok banget buat bot Telegram + Playwright yang gede image-nya.

---

## STEP 1: Isi Form "Create New Desktop"

Liat di console → menu kiri **Create New Desktop**. Isi dari atas ke bawah:

### 1.1. Choose Zone
Klik tab **Asia** → pilih **Singapore (Singapore)**. 🇸🇬

> Alternatif: Japan (Tokyo) juga oke, tapi Singapore lebih deket.

### 1.2. Choose Desktop OS
Klik **Ubuntu** (yang ada logo orange, biasanya paling kiri bawah).

> ⚠️ **PENTING**: Jangan pilih "Linux Mint" / "Fedora" / "Windows". Ubuntu paling familiar, paling banyak tutorial, dan dependency Playwright paling kompatibel. Versi LTS (Long Term Support) udah cukup.

Kalau ada dropdown versi, pilih **22.04 LTS** atau **24.04 LTS**.

> Catatan: UI Kamatera pakai kata "Desktop" tapi sebenernya ini VM/server (headless). Gak ada GUI desktop yang di-install. Bener-bener server, perfect buat bot.

### 1.3. Choose Server Specs
Bagian ini default-nya ke spec gede. **Turunkan ke yang minimum**:

| Field | Rekomendasi | Alasan |
|---|---|---|
| **TYPE** | **A** (Type A basic) | Paling murah, cukup buat bot |
| **CPU** | **1** | 1 core cukup — bot idle, sesekali spike pas restart |
| **RAM** | **1024 MB (1 GB)** | Minimum. Playwright ~300 MB pas idle, ~500 MB pas restart. Kalo mau lebih aman, pilih **2048 MB** (+$2/bulan). |
| **SSD DISK** | **20 GB** | Cukup buat OS (~5 GB) + Playwright/Chromium (~600 MB) + buffer |

> Klik **Detailed View** di kanan kalo mau liat harga per-config. Type A 1/1/20 biasanya paling murah.

Jangan centang:
- ❌ Daily Backup (gak perlu, bot bisa di-redeploy)
- ❌ Management Services (gak perlu, Momo handle sendiri via SSH)

### 1.4. Choose Networking
- ✅ Centang **Public Internet Network** (wajib, biar bisa SSH & bot bisa ke internet)
- ❌ Jangan centang Private Local Network (gak perlu)

### 1.5. Advanced Configuration
**Skip**, gak perlu diubah.

### 1.6. Finalize Settings
| Field | Isi |
|---|---|
| **Password** | Set password root yang kuat. **Catat baik-baik!** Ini password login SSH. |
| **Validate** | (Auto) |
| **Servers** | `1` |
| **Name #1** | Misal `ont-bot` (kasih nama biar gampang ditemuin di dashboard) |
| **Power On Servers** | Toggle **ON** (langsung nyala) |

### 1.7. Billing Cycle & Pricing
Pilih **Monthly Billing Cycle**. Selesai → klik **CREATE SERVER**.

> ⏱ Server biasanya jadi dalam 1-3 menit. Cek di menu **My Cloud → Servers** di sidebar kiri.

---

## STEP 2: Catat Info Server

Setelah server jadi, di **My Cloud → Servers** bakal ada list server baru. Klik nama server-nya, catat:

- **Public IP address** (misal `203.0.113.45`) — buat SSH
- **Username** (biasanya `root`)
- **Password** (yang Pak Boss set di step 1.6)

---

## STEP 3: SSH ke Server

### Di Windows pakai PowerShell atau Windows Terminal
```powershell
ssh root@203.0.113.45
```
Masukin password yang tadi. Kalau muncul warning "authenticity of host", ketik `yes` lalu enter.

### Di Mac/Linux
```bash
ssh root@203.0.113.45
```

Setelah masuk, lo bakal liat prompt:
```
root@ont-bot:~#
```

Artinya lo udah di dalam server. 🎉

> 💡 **Tips**: Gak wajib, tapi Momo saranin setup SSH key biar gak perlu ketik password tiap kali. Liat [appendix di bawah](#setup-ssh-key-opsional-tapi-recommended).

---

## STEP 4: Install Dependency di Server

Jalanin command-command ini **satu-satu** di SSH session. Momo udah grouping biar tinggal copy-paste.

### 4.1. Update OS & install base tools
```bash
apt update && apt upgrade -y
apt install -y git curl wget tini
```

### 4.2. Install Python 3.11+ via uv (lebih cepat dari apt)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv --version
```

### 4.3. Install dependency Playwright (system libs buat Chromium)
```bash
apt install -y --no-install-recommends \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
  fonts-liberation
```

> Catatan: nama package di Ubuntu 24.04 pakai suffix `t64` (libasound2t64). Di 22.04 biasa `libasound2`. Kalo error, sesuaikan.

### 4.4. Clone repo & setup Python
```bash
cd /opt
git clone https://github.com/USERNAME/ont-restart-bot.git
cd ont-restart-bot

# Create venv
uv venv .venv --python 3.11
source .venv/bin/activate

# Install deps
uv pip install -r requirements.txt

# Install Chromium browser
playwright install chromium
```

> ⚠️ **Ganti USERNAME** dengan username GitHub Pak Boss (atau pake upload manual via scp, lihat [appendix](#upload-file-tanpa-github)).

---

## STEP 5: Konfigurasi `.env`

```bash
cd /opt/ont-restart-bot
cp .env.example .env
nano .env
```

Isi semua value:

```env
TELEGRAM_BOT_TOKEN=<token dari @BotFather>
TELEGRAM_ALLOWED_USERS=123456789
ACSIS_BASE_URL=https://acs-ibooster.telkom.co.id
ACSIS_USERNAME=<username ACSIS>
ACSIS_PASSWORD=password_asli_pak_boss
ACSIS_LOGIN_OPTION=Telkom Akses
ACSIS_TOTP_SECRET=<secret TOTP>
LOG_LEVEL=INFO
TZ=Asia/Jakarta
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`.

> 💡 **Cara dapet `TELEGRAM_ALLOWED_USERS`**: Jalankan bot lokal di laptop **sekali aja** (`python bot.py`), terus chat `/myid` ke bot. Nanti bot reply user ID Telegram Pak Boss.

---

## STEP 6: Test Manual Dulu

```bash
cd /opt/ont-restart-bot
source .venv/bin/activate
python bot.py
```

Kalau jalan normal, bakal muncul log:
```
INFO Bot starting. Allowed users: [123456789]
```

Coba chat `/start` di Telegram. **Kalo udah respond, stop pake `Ctrl+C`** — ini cuma test.

Kalo ada error, share error message-nya ke Momo biar bisa debug.

---

## STEP 7: Setup Systemd Service (Auto-Start 24/7)

Bot ini harus jalan terus, restart otomatis kalo server reboot. Pakai systemd.

### 7.1. Bikin service file
```bash
cat > /etc/systemd/system/ont-bot.service <<'EOF'
[Unit]
Description=ONT Restart Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ont-restart-bot
Environment="PATH=/opt/ont-restart-bot/.venv/bin"
EnvironmentFile=/opt/ont-restart-bot/.env
ExecStart=/opt/ont-restart-bot/.venv/bin/python -u /opt/ont-restart-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/ont-bot.log
StandardError=append:/var/log/ont-bot.log

[Install]
WantedBy=multi-user.target
EOF
```

### 7.2. Enable & start
```bash
systemctl daemon-reload
systemctl enable ont-bot
systemctl start ont-bot
```

### 7.3. Cek status
```bash
systemctl status ont-bot
```

Harus muncul `Active: active (running)`. Kalo error, cek log:
```bash
tail -50 /var/log/ont-bot.log
```

---

## STEP 8: Verifikasi & Test End-to-End

1. Buka Telegram → chat bot
2. `/start` → harusnya bot reply menu
3. `/restart 122868308296` → tunggu 15-60 detik → harusnya bot lapor "Berhasil" / "Gagal"

Kalo respon-nya bener, **selesai!** 🎉 Bot udah jalan 24/7 di Singapore.

---

## Maintenance Commands (buat nanti)

| Task | Command |
|---|---|
| Liat log realtime | `journalctl -u ont-bot -f` |
| Restart bot | `systemctl restart ont-bot` |
| Stop bot | `systemctl stop ont-bot` |
| Update code | `cd /opt/ont-restart-bot && git pull && systemctl restart ont-bot` |
| Liat 100 log terakhir | `journalctl -u ont-bot -n 100 --no-pager` |
| Disk usage | `df -h` |
| Memory usage | `free -h` |
| CPU usage | `top` (exit: `q`) |

---

## Setup SSH Key (opsional tapi recommended)

Daripada ketik password tiap SSH, mending pake SSH key.

### Di laptop Windows (PowerShell)
```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\kamatera_key
type $HOME\.ssh\kamatera_key.pub | ssh root@203.0.113.45 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Di laptop Mac/Linux
```bash
ssh-keygen -t ed25519 -f ~/.ssh/kamatera_key
ssh-copy-id -i ~/.ssh/kamatera_key.pub root@203.0.113.45
```

Habis itu, biar gampang:
```bash
# Di ~/.ssh/config (laptop)
Host kamatera
  HostName 203.0.113.45
  User root
  IdentityFile ~/.ssh/kamatera_key
```

Sekarang `ssh kamatera` langsung masuk tanpa password.

---

## Upload File Tanpa GitHub

Kalo males pake GitHub, bisa upload langsung dari laptop:

```bash
# Dari laptop, archive project
cd "C:\Users\ASUS\WorkBuddy AI\Claw\ont-restart-bot"
# exclude .venv
tar -czf ont-restart-bot.tar.gz --exclude='.venv' --exclude='__pycache__' .

# Upload via SCP
scp ont-restart-bot.tar.gz root@203.0.113.45:/opt/

# Di server
cd /opt
tar -xzf ont-restart-bot.tar.gz -C ont-restart-bot/
```

> Saran Momo: tetep pake GitHub, jauh lebih gampang buat update. Push dari lokal, di server tinggal `git pull`.

---

## Troubleshooting

### Build gagal / Playwright gak bisa install Chromium
```bash
# Cek versi OS
cat /etc/os-release
# Install manual Chromium (fallback)
playwright install --with-deps chromium
```

### Bot start tapi gak respond di Telegram
```bash
# Cek log
journalctl -u ont-bot -n 50
# Cek network keluar (harus bisa ke Telegram + ACSIS)
curl -I https://api.telegram.org
curl -I https://acs-ibooster.telkom.co.id
```

### TOTP invalid terus
- Cek `TZ=Asia/Jakarta` di `.env`
- Cek jam server: `date` (harus sesuai Asia/Jakarta)
- Kalo salah timezone: `timedatectl set-timezone Asia/Jakarta`

### Server lambat / timeout
- Cek memory: `free -h`. Kalo swap 0 dan RAM penuh, upgrade spec.
- Cek disk: `df -h`. Kalo penuh, bersihin log: `journalctl --vacuum-time=7d`

### Password SSH ditolak terus
- Di Kamatera console → My Cloud → Servers → klik server → "Reset Password" (reset root password via console)
- Akses via VNC di console Kamatera (tombol "Open Console" di dashboard server)

---

## Biaya Estimate

| Spec | Harga/bulan |
|---|---|
| Type A 1 CPU / 1 GB RAM / 20 GB SSD | ~$4 |
| Type A 1 CPU / 2 GB RAM / 20 GB SSD | ~$6 (recommended) |
| Type B 2 CPU / 2 GB RAM / 20 GB SSD | ~$8 (kalau mau lebih kenceng) |

> Kamatera free trial biasanya kasih credit $100 buat testing. Cek di console → Billing.

---

## Backup Strategy (opsional)

Bot ini stateless — code di `/opt/ont-restart-bot`, data cuma di `.env`. Gampang restore:

1. Setup lengkap ulang (Step 1-7) di server baru
2. Push `.env` ke server baru
3. Done ~10 menit

Atau pake GitHub: push code + `.env.example` (JANGAN push `.env` asli). Restore = `git clone` di server baru.

---

## Ringkasan (TLDR)

```bash
# 1. Di laptop, push code ke GitHub
cd "C:\Users\ASUS\WorkBuddy AI\Claw\ont-restart-bot"
git init && git add . && git commit -m "init"
git remote add origin https://github.com/USERNAME/ont-restart-bot.git
git push -u origin main

# 2. Di Kamatera console, create Ubuntu 22.04 di Singapore
#    1 CPU, 1 GB RAM, 20 GB SSD, set password root

# 3. SSH ke server, paste:
ssh root@YOUR_SERVER_IP
# ... terus semua command dari Step 4-7 di atas
```
