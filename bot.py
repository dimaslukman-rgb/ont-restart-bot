"""Telegram bot buat trigger restart ONT via ACSIS ibooster."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import traceback
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

# ========== ENHANCED LOGGING ==========
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("telegram").setLevel(logging.DEBUG)
logging.getLogger("apscheduler").setLevel(logging.DEBUG)
# ======================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USERS: set[int] = {
    int(uid)
    for uid in re.split(r"[\s,]+", os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if uid.strip().isdigit()
}

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN belum di-set di .env")

logger.info("=== BOT STARTUP ===")
logger.info("ALLOWED_USERS: %s", sorted(ALLOWED_USERS) if ALLOWED_USERS else "<ALL>")
logger.info("ACSIS_USERNAME: %s", os.environ.get("ACSIS_USERNAME", "NOT SET"))
logger.info("ACSIS_BASE_URL: %s", os.environ.get("ACSIS_BASE_URL", "NOT SET"))
logger.info("LOG_LEVEL: %s", os.environ.get("LOG_LEVEL", "INFO"))

def is_authorized(user_id: int) -> bool:
    return not ALLOWED_USERS or user_id in ALLOWED_USERS

def build_client(on_progress=None):
    try:
        return AcsisClient(
            base_url=os.environ.get("ACSIS_BASE_URL", "https://acs-ibooster.telkom.co.id"),
            username=os.environ["ACSIS_USERNAME"],
            password=os.environ["ACSIS_PASSWORD"],
            login_option=os.environ.get("ACSIS_LOGIN_OPTION", "Telkom Akses"),
            totp_secret=os.environ["ACSIS_TOTP_SECRET"],
            headless=os.environ.get("ACSIS_HEADLESS", "true").lower() != "false",
            debug_screenshot_dir=os.environ.get("DEBUG_SCREENSHOT_DIR") or None,
            on_progress=on_progress,
        )
    except KeyError as e:
        logger.error("Missing env var: %s", e.args[0])
        raise SystemExit(
            f"Environment variable {e.args[0]} belum di-set. Lihat .env.example."
        ) from e

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/start received from user_id=%s, chat_id=%s", update.effective_user.id, update.effective_chat.id)
    if not is_authorized(update.effective_user.id):
        logger.warning("Unauthorized access from user_id=%s", update.effective_user.id)
        return await update.message.reply_text("Akses ditolak. User ID kamu belum whitelist.")
    await update.message.reply_text(
        "👋 *ONT Restart Bot*\n\nPerintah:\n• `/restart <no_internet>` — restart ONT\n• `/test` — smoke test\n• `/help` — tips\n• `/myid` — cek ID\n\nBot nge-drive browser headless ke ACSIS.",
        parse_mode="Markdown",
    )
    logger.info("/start completed for user_id=%s", update.effective_user.id)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/help from user_id=%s", update.effective_user.id)
    if not is_authorized(update.effective_user.id):
        return await update.message.reply_text("Akses ditolak.")
    await update.message.reply_text("Help", parse_mode="Markdown")

async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/myid from user_id=%s", update.effective_user.id)
    await update.message.reply_text(f"User ID: {update.effective_user.id}", parse_mode="Markdown")

async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info("/restart received from user_id=%s, chat_id=%s, args=%s", user_id, chat_id, ctx.args)
    if not is_authorized(user_id):
        logger.warning("Unauthorized restart from user_id=%s", user_id)
        return await update.message.reply_text("Akses ditolak.")
    if not ctx.args:
        return await update.message.reply_text("Format: /restart <no_internet>", parse_mode="Markdown")

    no_internet = ctx.args[0].strip()
    logger.info("Processing restart for no_internet=%s", no_internet)

    lock = ctx.chat_data.get("lock")
    if lock is None:
        lock = asyncio.Lock()
        ctx.chat_data["lock"] = lock
    if lock.locked():
        logger.warning("Restart already running in chat_id=%s", chat_id)
        return await update.message.reply_text("Lagi ada restart yang jalan di chat ini. Sabar ya.")

    async with lock:
        status = await update.message.reply_text(f"Restart ONT {no_internet}...\nStep: login → OTP → search → restart. Sabar 15–60 detik.", parse_mode="Markdown")
        await ctx.application.bot.send_chat_action(chat_id, ChatAction.TYPING)

        try:
            client = build_client(on_progress=lambda msg: logger.info("[Progress] %s", msg))
            logger.info("Calling restart_ont for %s", no_internet)
            result = await client.restart_ont(no_internet)
            logger.info("restart_ont completed: success=%s, duration=%ss", result.success, result.duration_sec)
        except Exception as e:
            logger.exception("Unhandled error di restart untuk %s: %s", no_internet, e)
            return await status.edit_text("Error internal. Cek log di Railway.")

        if result.success:
            text = f"✅ Berhasil! ONT {result.no_internet} restart. Durasi: {result.duration_sec}s"
        else:
            step_hint = f" (gagal di step: {result.failed_step})" if result.failed_step else ""
            text = f"❌ Gagal restart ONT {result.no_internet}{step_hint}. {result.message}"
        await status.edit_text(text, parse_mode="Markdown")
        logger.info("Restart response sent: success=%s", result.success)

async def cmd_test(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/test from user_id=%s", update.effective_user.id)
    if not is_authorized(update.effective_user.id):
        return await update.message.reply_text("Akses ditolak.")
    await update.message.reply_text("Test OK", parse_mode="Markdown")

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot ini nge-run step-nya langsung.")

async def on_unhandled(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        logger.debug("Unhandled: %s", update.message.text[:50])
        await update.message.reply_text("Gue cuma ngerti perintah. Coba /help")

async def post_init(application: Application) -> None:
    logger.info("=== BOT STARTED POLLING ===")
    logger.info("Allowed users: %s", sorted(ALLOWED_USERS) if ALLOWED_USERS else "<ALL>")

async def post_shutdown(application: Application) -> None:
    logger.info("=== BOT SHUTDOWN ===")

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_unhandled))
    app.post_init = post_init
    app.post_shutdown = post_shutdown
    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("FATAL ERROR: %s", e)
        traceback.print_exc()
        raise
