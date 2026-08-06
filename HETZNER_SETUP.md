# Deploy ke Hetzner Cloud ☁️🇩🇪

Panduan lengkap dari **0 (signup)** sampai bot jalan 24/7 di Hetzner Cloud (free trial 30 hari, ~€20 credit).

## Kenapa Hetzner oke buat bot ini

| Aspek | Detail |
|---|---|
| Free credit | **€20 untuk 30 hari** (~Rp 350rb) |
| UI | Super clean, gak ada WAN detection aneh (banding sama Kamatera) |
| Region | FAL (Frankfurt), NBG (Nuremberg), HEL (Helsinki), ASH (Ashburn US) |
| Performa | NVMe SSD, network 1 Gbps — kenceng |
| Support | Bagus, response cepet |
| Signup | Kartu kredit / PayPal required, tapi **gak di-charge** selama trial |
| Cukup buat | CX22 (2 vCPU, 4 GB RAM, 40 GB SSD) ~ 4 bulan masa trial |

> Estimasi biaya setelah trial: **€4.85/bulan** (~$5) buat CX22 — sangat worth it.

---

## STEP 1: Signup (kalau belum)

1. Buka https://console.hetzner.cloud
2. Klik **Sign in** (kalau udah punya akun) atau **Sign up** (kalau baru)
3. Isi form: Individual, nama, alamat, telepon
4. **VAT ID kosongin** (gak support Indonesia, gak wajib)
5. Save & continue → registration successful

## STEP 2: Setup Payment Method

1. Hetzner Cloud Console → klik nama akun (kanan atas) → **Billing**
2. Tab **Payment methods** → **Add payment method**
3. Pilih **Credit card** atau **PayPal**
4. Isi data → confirm

> ⚠️ Kalo payment method ditolak (Indonesia sering kena fraud check):
> - Coba pake PayPal
> - Atau virtual credit card (Jenius / Jago)
> - Kalo masih ditolak → pivot ke **Google Cloud e2-micro** (always free)

## STEP 3: Create Project + Server

### 3.1. New Project
1. Console → **New Project** → kasih nama `ont-bot`
2. Klik project

### 3.2. New Server
1. Klik **+ NEW SERVER** (tombol hijau di tengah)
2. Isi form:

| Field | Pilih |
|---|---|
| **Location** | **FAL (Frankfurt)** atau NBG — deket Asia routing bagus |
| **Image** | **Ubuntu 24.04** (atau 22.04) |
| **Type** | **CX22** (Shared, 2 vCPU, 4 GB RAM, 40 GB SSD) — €4.85/bulan |
| **Networking** | IPv4: ✅. IPv6: opsional (matiin aja biar simple) |
| **SSH keys** | Skip dulu, pake password root aja |
| **Volumes** | Skip |
| **Backups** | Skip (gak perlu, bot stateless) |
| **Cloud-init** | Skip |
| **Name** | `ont-bot` |

3. Klik **CREATE & BUY NOW**

> ⏱ Server jadi dalam ~30 detik. Tunggu sampai status **Running**.

## STEP 4: Catat IP Server

Setelah server jadi, di list server bakal keliatan:
- **Public IPv4**: misal `78.46.123.45` ← INI YANG KITA BUTUHKAN
- Status: running

---

## STEP 5: SSH ke Server

### Di Windows (PowerShell)
```powershell
ssh root@78.46.123.45
```
Masukin password root yang Hetzner kasih (di console → klik server → "Reset root password" kalo lupa, atau pas create ada pilihan set password).

### Di Mac/Linux
```bash
ssh root@78.46.123.45
```

Prompt sukses:
```
root@ont-bot:~#
```

> 💡 **Rekomendasi**: Setup SSH key biar gak perlu ketik password. Lihat [appendix](#setup-ssh-key-recommended).

---

## STEP 6: Install Dependency

Copy-paste command ini **satu-satu** di SSH session. Momo udah grouping.

### 6.1. Update OS & base tools
```bash
apt update && apt upgrade -y
apt install -y git curl wget tini ufw
```

### 6.2. Setup firewall (opsional tapi recommended)
```bash
ufw allow OpenSSH
ufw enable
# Confirm dengan 'y' kalo ditanya
```

### 6.3. Install Python 3.11+ via uv (lebih cepat dari apt)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv --version
```

### 6.4. Install system dependencies Playwright
```bash
apt install -y --no-install-recommends \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
  fonts-liberation
```

> Di Ubuntu 24.04: `libasound2t64`. Di 22.04: `libasound2`. Sesuaikan kalo error.

### 6.5. Clone repo & setup Python
```bash
cd /opt
# Pakai git clone atau upload manual via scp - lihat appendix

# Opsi A: dari GitHub (kalau udah push)
git clone https://github.com/USERNAME/ont-restart-bot.git

# Opsi B: dari laptop via SCP (kalau gak mau GitHub)
# Di laptop, jalankan:
# scp -r "C:\Users\ASUS\WorkBuddy AI\Claw\ont-restart-bot" root@78.46.123.45:/opt/

cd ont-restart-bot
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
playwright install chromium
```

### 6.6. Set timezone
```bash
timedatectl set-timezone Asia/Jakarta
# Verifikasi
date
```

---

## STEP 7: Konfigurasi `.env`

```bash
cd /opt/ont-restart-bot
cp .env.example .env
nano .env
```

Isi semua:
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

> 💡 **`TELEGRAM_ALLOWED_USERS`**: User ID Telegram Pak Boss. Cara dapet: jalanin bot lokal sekali (`python bot.py`), chat `/myid` di Telegram, catat ID-nya.

---

## STEP 8: Test Manual Dulu

```bash
cd /opt/ont-restart-bot
source .venv/bin/activate
python bot.py
```

Kalo jalan, log-nya:
```
INFO Bot starting. Allowed users: [123456789]
```

Coba chat `/start` di Telegram. **Stop dengan `Ctrl+C`** kalo udah respond.

---

## STEP 9: Setup Systemd Service (Auto-Start 24/7)

### 9.1. Bikin service file
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

### 9.2. Enable & start
```bash
systemctl daemon-reload
systemctl enable ont-bot
systemctl start ont-bot
```

### 9.3. Cek status
```bash
systemctl status ont-bot
```

Harus `Active: active (running)`. Kalo error, cek log:
```bash
tail -50 /var/log/ont-bot.log
```

---

## STEP 10: Verifikasi

1. Telegram → chat bot
2. `/start` → harus reply menu
3. `/restart 122868308296` → tunggu 15-60 detik → lapor hasil

✅ Beres — bot 24/7! 🎉

---

## Maintenance Commands

| Task | Command |
|---|---|
| Liat log realtime | `journalctl -u ont-bot -f` |
| Restart bot | `systemctl restart ont-bot` |
| Stop bot | `systemctl stop ont-bot` |
| Liat 100 log terakhir | `journalctl -u ont-bot -n 100 --no-pager` |
| Disk usage | `df -h` |
| Memory usage | `free -h` |
| Update code | `cd /opt/ont-restart-bot && git pull && systemctl restart ont-bot` |
| Hapus server | Hetzner Console → server → Delete |

---

## Setup SSH Key (Recommended)

Daripada ketik password tiap SSH, pake SSH key.

### Di laptop Windows (PowerShell)
```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\hetzner_key
type $HOME\.ssh\hetzner_key.pub | ssh root@78.46.123.45 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Di laptop Mac/Linux
```bash
ssh-keygen -t ed25519 -f ~/.ssh/hetzner_key
ssh-copy-id -i ~/.ssh/hetzner_key.pub root@78.46.123.45
```

Biar gampang, tambahin ke `~/.ssh/config` (laptop):
```
Host hetzner
  HostName 78.46.123.45
  User root
  IdentityFile ~/.ssh/hetzner_key
```

Sekarang `ssh hetzner` langsung masuk.

---

## Upload Code Tanpa GitHub

Kalo males pake GitHub, upload dari laptop:

```powershell
# Di laptop (PowerShell)
scp -r "C:\Users\ASUS\WorkBuddy AI\Claw\ont-restart-bot" root@78.46.123.45:/opt/
```

> Tapi Momo recommend push ke GitHub — gampang update nanti tinggal `git pull`.

---

## Troubleshooting

### Payment method ditolak
- Coba pake PayPal (lebih friendly buat akun non-EU)
- Virtual CC dari Jenius / Jago bisa dicoba
- Kalo masih ditolak → pivot ke Google Cloud e2-micro (always free)

### SSH connection refused
```bash
# Cek status server di Hetzner console
# Kalo running tapi SSH gak masuk, kemungkinan firewall Hetzner block IP
# Solusi: Hetzner Console → server → tab "Firewalls" → add rule allow SSH from any
```

### Build Playwright gagal (missing libs)
```bash
# Cek OS version
cat /etc/os-release
# Install deps manual
playwright install-deps chromium
```

### TOTP invalid terus
- Cek `TZ=Asia/Jakarta` di `.env`
- Cek `date` di server (harus sesuai Asia/Jakarta)
- Kalo salah timezone: `sudo timedatectl set-timezone Asia/Jakarta`

### Bot gak respond
```bash
# Cek log
journalctl -u ont-bot -n 50
# Cek network keluar
curl -I https://api.telegram.org
curl -I https://acs-ibooster.telkom.co.id
```

### Habis masa trial
- Hetzner otomatis charge ke payment method kalo gak cancel
- Cancel: Console → Project → Settings → Cancel project (sebelum hari ke-30)
- Atau set reminder: 25 hari lagi review, mau lanjut atau stop

---

## Biaya Reference

| Spec | Harga | Bisa buat |
|---|---|---|
| CX22 (2 vCPU / 4 GB / 40 GB) | €4.85/bulan | ~4 bulan masa trial €20 |
| CPX21 (3 vCPU / 4 GB / 80 GB) | €7.85/bulan | ~2.5 bulan |
| CAX11 (ARM, 2 vCPU / 4 GB / 40 GB) | €3.79/bulan | ~5 bulan (ARM, lebih murah) |

> 💡 Pak Boss bisa **ganti ke CAX11 (ARM)** kalo mau lebih hemat. Tapi perlu test kompatibilitas Python wheel di ARM. Buat amannya, CX22 aman.

---

## TLDR (versi pendek)

```bash
# 1. Signup di hetzner.cloud (form contact + payment method)
# 2. Create project + CX22 Ubuntu 24.04 di FAL
# 3. SSH ke IP server
# 4. Paste command di Step 6 (install deps)
# 5. Clone code, setup .env
# 6. Setup systemd (Step 9)
# 7. Test di Telegram
```

Done! 🎉
