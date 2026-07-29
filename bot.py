"""Telegram bot buat trigger restart ONT via ACSIS ibooster."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from automation import AcsisAutomationError, AcsisClient, RestartResult

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------- config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USERS: set[int] = {
    int(uid)
    for uid in re.split(r"[\s,]+", os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if uid.strip().isdigit()
}

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN belum di-set di .env")


# --------------------------------------------------------------------- helpers
def is_authorized(user_id: int) -> bool:
    """Kalau ALLOWED_USERS kosong, semua orang boleh (fallback)."""
    return not ALLOWED_USERS or user_id in ALLOWED_USERS


def build_client() -> AcsisClient:
    try:
        return AcsisClient(
            base_url=os.environ.get("ACSIS_BASE_URL", "https://acs-ibooster.telkom.co.id"),
            username=os.environ["ACSIS_USERNAME"],
            password=os.environ["ACSIS_PASSWORD"],
            login_option=os.environ.get("ACSIS_LOGIN_OPTION", "Telkom Akses"),
            totp_secret=os.environ["ACSIS_TOTP_SECRET"],
            headless=os.environ.get("ACSIS_HEADLESS", "true").lower() != "false",
            debug_screenshot_dir=os.environ.get("DEBUG_SCREENSHOT_DIR") or None,
        )
    except KeyError as e:
        raise SystemExit(
            f"Environment variable {e.args[0]} belum di-set. Lihat .env.example."
        ) from e


# ------------------------------------------------------------------- commands
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.effective_user.id):
        return await update.message.reply_text("Akses ditolak. User ID kamu belum whitelist.")
    await update.message.reply_text(
        "👋 *ONT Restart Bot*\n\n"
        "Perintah yang tersedia:\n"
        "• `/restart <no_internet>` — restart ONT\n"
        "• `/help` — contoh & tips\n"
        "• `/myid` — cek Telegram user ID kamu\n\n"
        "Bot ini nge-drive browser headless ke ACSIS, "
        "jadi pastikan server yang jalanin bot punya akses internet ke "
        "`acs-ibooster.telkom.co.id`.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.effective_user.id):
        return await update.message.reply_text("Akses ditolak.")
    await update.message.reply_text(
        "*Cara pakai:*\n"
        "1. Siapkan No Internet (contoh: `122868308296`)\n"
        "2. Kirim: `/restart 122868308296`\n"
        "3. Tunggu 15–60 detik. Bot lapor hasilnya.\n\n"
        "*Catatan:*\n"
        "• 1 task = 1 eksekusi penuh (login → OTP → search → restart)\n"
        "• Tiap 1 user gabisa pake bot barengan (lock per chat)\n"
        "• Kalo gagal, balasan bot akan kasih pesan error yang bisa di-trace",
        parse_mode="Markdown",
    )


async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"User ID kamu: `{update.effective_user.id}`", parse_mode="Markdown"
    )


async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.effective_user.id):
        return await update.message.reply_text("Akses ditolak.")
    if not ctx.args:
        return await update.message.reply_text(
            "Format: `/restart <no_internet>`\nContoh: `/restart 122868308296`",
            parse_mode="Markdown",
        )

    no_internet = ctx.args[0].strip()
    chat_id = update.effective_chat.id

    # Lock sederhana: gabisa restart paralel di chat yang sama.
    lock: Optional[asyncio.Lock] = ctx.chat_data.get("lock")
    if lock is None:
        lock = asyncio.Lock()
        ctx.chat_data["lock"] = lock
    if lock.locked():
        return await update.message.reply_text(
            "Lagi ada restart yang jalan di chat ini. Sabar ya."
        )

    async with lock:
        status = await update.message.reply_text(
            f"⏳ *Restart ONT `{no_internet}`...*\n"
            "Step: login → OTP → search → restart. Sabar 15–60 detik.",
            parse_mode="Markdown",
        )
        await ctx.application.bot.send_chat_action(chat_id, ChatAction.TYPING)

        try:
            client = build_client()
            result: RestartResult = await client.restart_ont(no_internet)
        except AcsisAutomationError as e:
            logger.warning("AcsisAutomationError: %s", e)
            return await status.edit_text(f"❌ Gagal: {e}")
        except Exception:  # noqa: BLE001
            logger.exception("Unhandled error di restart")
            return await status.edit_text("❌ Error internal. Cek log di server.")

        if result.success:
            text = (
                f"✅ *Berhasil!* ONT `{result.no_internet}` sudah di-restart.\n"
                f"⏱ Durasi: {result.duration_sec} detik"
            )
        else:
            text = f"❌ *Gagal* restart ONT `{result.no_internet}`.\n{result.message}"
        await status.edit_text(text, parse_mode="Markdown")


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder: TOTP & navigasi udah otomatis, jadi cancel biasanya gpp di-skip."""
    await update.message.reply_text(
        "Bot ini nge-run step-nya langsung (gak ada state yang bisa di-cancel). "
        "Kalo lagi nge-hang, tunggu — bakal timeout sendiri max ~1 menit."
    )


async def on_unhandled(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        await update.message.reply_text(
            "Gue cuma ngerti perintah. Coba `/help` buat liat list-nya."
        )


# --------------------------------------------------------------------- main
def main() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=os.environ.get("LOG_LEVEL", "INFO"),
    )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_unhandled))

    logger.info(
        "Bot starting. Allowed users: %s",
        sorted(ALLOWED_USERS) if ALLOWED_USERS else "<ALL — set TELEGRAM_ALLOWED_USERS>",
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
