"""Playwright automation buat ACSIS ibooster (Telkom)."""
from __future__ import annotations

import asyncio
import gc
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import pyotp
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

logger = logging.getLogger(__name__)


@dataclass
class RestartResult:
    success: bool
    message: str
    no_internet: str = ""
    duration_sec: float = 0.0
    dialogs_seen: list[str] = field(default_factory=list)
    failed_step: str = ""  # Step mana yang macet (kalau gagal)


class AcsisAutomationError(Exception):
    """Error umum waktu automation jalan."""

    def __init__(self, message: str, step: str = ""):
        super().__init__(message)
        self.step = step


class AcsisClient:
    """Client buat nge-drive browser ke halaman ACSIS ibooster."""

    BASE_URL_DEFAULT = "https://acs-ibooster.telkom.co.id"
    DEFAULT_TIMEOUT_MS = 30_000

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        login_option: str,
        totp_secret: str,
        *,
        headless: bool = True,
        debug_screenshot_dir: Optional[str] = None,
        on_progress=None,  # callable(str) → optional, dipanggil tiap step
    ) -> None:
        if not totp_secret:
            raise ValueError("TOTP secret kosong. Isi ACSIS_TOTP_SECRET di .env")
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.login_option = login_option
        self.totp = pyotp.TOTP(totp_secret.replace(" ", "").replace("=", ""))
        self.headless = headless
        self.debug_dir = debug_screenshot_dir or ""
        self.on_progress = on_progress or (lambda msg: None)

    # ------------------------------------------------------------------ public
    async def restart_ont(self, no_internet: str) -> RestartResult:
        no_internet = (no_internet or "").strip()
        if not no_internet.isdigit() or len(no_internet) < 8:
            return RestartResult(
                success=False,
                message="No Internet harus angka, minimal 8 digit.",
                no_internet=no_internet,
            )

        started = time.monotonic()
        dialogs: list[str] = []
        logger.info(
            "=== Starting Playwright automation (no_internet=%s, headless=%s) ===",
            no_internet,
            self.headless,
        )

        async with async_playwright() as p:
            logger.info("Playwright siap - launch Chromium...")
            self._log_memory("sebelum launch")
            try:
                # Memory-efficient Chromium launch. Railway free tier = 512 MB,
                # Playwright default args bisa spike 800 MB+ dan OOM-kill.
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",  # /dev/shm kecil di container
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-default-apps",
                        "--disable-sync",
                        "--disable-translate",
                        "--no-first-run",
                        "--no-zygote",
                        "--single-process",  # Hemat ~30% memory (trade-off: kurang stabil)
                        # --proxy-server='direct://' (ikut tanda kutip) bikin Chromium
                        # resolve hostname sampah -> DNS gagal. --no-proxy-server lebih bener.
                        "--no-proxy-server",
                    ],
                )
                logger.info("Chromium berhasil diluncurkan.")
                self._log_memory("sesudah launch")
            except Exception as e:  # noqa: BLE001
                raise AcsisAutomationError(
                    f"Gagal launch Chromium (kemungkinan OOM): {e}", step="launch"
                ) from e

            context: Optional[BrowserContext] = None
            page: Optional[Page] = None
            try:
                context = await self._new_context(browser)
                logger.info("Browser context OK.")
                page = await context.new_page()
                logger.info(
                    "Page OK - set default timeout %sms.", self.DEFAULT_TIMEOUT_MS
                )
                page.set_default_timeout(self.DEFAULT_TIMEOUT_MS)
                page.set_default_navigation_timeout(self.DEFAULT_TIMEOUT_MS)
                self._wire_dialog_handler(page, dialogs)
                logger.info("Dialog handler aktif.")

                logger.info("[step 1/4] Login...")
                await self._login(page)
                logger.info("[step 1/4] Login selesai.")
                logger.info("[step 2/4] Submit OTP...")
                await self._submit_otp(page)
                logger.info("[step 2/4] OTP selesai.")
                logger.info("[step 3/4] Search ONT...")
                await self._search_internet(page, no_internet)
                logger.info("[step 3/4] Search selesai.")
                logger.info("[step 4/4] Trigger restart...")
                await self._trigger_restart(page, dialogs)
                logger.info("[step 4/4] Restart selesai.")
            finally:
                if page is not None:
                    await self._maybe_screenshot(page, "final")
                if context is not None:
                    try:
                        await context.close()
                    except Exception:  # noqa: BLE001
                        logger.warning("Gagal close context (mungkin udah crash)")
                try:
                    await browser.close()
                except Exception:  # noqa: BLE001
                    logger.warning("Gagal close browser (mungkin udah crash)")

        duration = time.monotonic() - started
        gc.collect()  # Force GC buat release memory sebelum exit
        self._log_memory("final")
        logger.info(
            "=== Automation selesai: %.1fs, %d dialog, success=%s ===",
            duration,
            len(dialogs),
            any(re.search(r"Berhasil", d, re.I) for d in dialogs),
        )
        return self._interpret(no_internet, dialogs, duration)

    # ------------------------------------------------------------------ helpers
    async def _new_context(self, browser: Browser) -> BrowserContext:
        return await browser.new_context(
            viewport={"width": 1366, "height": 820},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
        )

    @staticmethod
    def _log_memory(label: str) -> None:
        """Log RSS memory (KB) biar bisa deteksi OOM pressure di Railway."""
        try:
            import resource
            import sys

            rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin":
                rss_kb //= 1024  # macOS: bytes; Linux: KB
            logger.info("[mem:%s] max RSS ~%.1f MB", label, rss_kb / 1024.0)
        except Exception:  # noqa: BLE001
            logger.debug("resource module gak tersedia di platform ini")

    @staticmethod
    def _wire_dialog_handler(page: Page, dialogs: list[str]) -> None:
        async def handler(dialog) -> None:
            msg = dialog.message or ""
            dialogs.append(msg)
            logger.info("[dialog] %s", msg)
            try:
                await dialog.accept()
            except Exception:  # noqa: BLE001
                logger.exception("Gagal accept dialog")

        page.on("dialog", lambda d: asyncio.create_task(handler(d)))

    async def _login(self, page: Page) -> None:
        self.on_progress("🔐 Membuka halaman login...")
        logger.info("Membuka halaman login: %s/login", self.base_url)
        await page.goto(f"{self.base_url}/login", wait_until="domcontentloaded")
        logger.info("Halaman login termuat.")
        await self._maybe_screenshot(page, "01_login")

        # Username: input teks pertama yang visible (yang ada icon orang).
        username_input = page.locator(
            'input[type="text"]:visible, input:not([type]):visible, '
            'input[name="username"]:visible, input[autocomplete="username"]:visible'
        ).first
        await username_input.fill(self.username)

        # Password
        await page.locator('input[type="password"]:visible').first.fill(self.password)

        # Dropdown role: pilih berdasarkan label visible.
        select = page.locator("select:visible").first
        await select.wait_for(state="visible", timeout=10_000)
        # Coba beberapa strategi select
        try:
            await select.select_option(label=self.login_option)
        except Exception:  # noqa: BLE001
            try:
                await select.select_option(value=self.login_option)
            except Exception:  # noqa: BLE001
                # Fallback: cari <option> dengan text match
                await page.locator(
                    f"select option:has-text(\"{self.login_option}\")"
                ).first.evaluate(
                    "(el, sel) => { el.value = sel; el.dispatchEvent(new Event('change', {bubbles:true})); }",
                    self.login_option,
                )

        # Klik tombol Login (warna merah, persis "Login").
        await page.get_by_role("button", name=re.compile(r"^Login$", re.I)).click()
        await self._maybe_screenshot(page, "02_after_login_click")

        # Tunggu redirect ke /otp
        try:
            await page.wait_for_url(re.compile(r"/otp($|\?)"), timeout=15_000)
        except PlaywrightTimeoutError as e:
            raise AcsisAutomationError(
                "Gagal masuk ke halaman OTP. Cek username/password/dropdown.",
                step="login",
            ) from e

        self.on_progress("🔐 Login OK, masuk halaman OTP.")
        logger.info("Berhasil masuk halaman OTP.")

    async def _submit_otp(self, page: Page) -> None:
        self.on_progress("🔢 Generate & submit OTP...")
        otp_code = self.totp.now()
        logger.info("OTP di-generate (disembunyikan di log).")

        # Strategi: cari 6 input terpisah (maxlength=1) ATAU satu input numeric.
        single_char = page.locator('input[maxlength="1"]:visible')
        count = await single_char.count()

        if count >= 6:
            for i, digit in enumerate(otp_code[:6]):
                await single_char.nth(i).click()
                await single_char.nth(i).press(digit)
        else:
            # Input tunggal: isi sekaligus (umumnya auto-advance).
            target = page.locator(
                'input[inputmode="numeric"]:visible, '
                'input[type="tel"]:visible, '
                'input[autocomplete="one-time-code"]:visible'
            ).first
            if await target.count() == 0:
                # Last resort: input pertama yang terlihat di form OTP.
                target = page.locator('form input:visible').first
            await target.fill(otp_code)
            # Trigger input event buat beberapa implementasi custom.
            await target.evaluate(
                "(el) => el.dispatchEvent(new Event('input', {bubbles: true}))"
            )

        await self._maybe_screenshot(page, "03_otp_filled")
        await page.get_by_role("button", name=re.compile(r"^Verify$", re.I)).click()

        try:
            await page.wait_for_url(re.compile(r"/home($|\?)"), timeout=15_000)
        except PlaywrightTimeoutError as e:
            raise AcsisAutomationError(
                "Gagal masuk ke halaman Home. OTP kemungkinan salah / expired.",
                step="otp",
            ) from e

        self.on_progress("✅ OTP OK, masuk halaman Home.")
        logger.info("Berhasil masuk halaman Home.")

    async def _search_internet(self, page: Page, no_internet: str) -> None:
        self.on_progress(f"🔍 Cari data ONT {no_internet}...")
        # Tunggu form pencarian muncul.
        no_inet_input = page.locator(
            'input[placeholder*="internet" i]:visible, '
            'input[type="text"]:visible'
        ).first
        await no_inet_input.wait_for(state="visible", timeout=10_000)
        await no_inet_input.fill(no_internet)

        await self._maybe_screenshot(page, "04_internet_filled")
        await page.get_by_role("button", name=re.compile(r"^CEK$", re.I)).click()

        # Tunggu sampai tabel fiber info muncul (cek ada teks "Fiber Information").
        try:
            await page.get_by_text("Fiber Information", exact=False).first.wait_for(
                state="visible", timeout=15_000
            )
        except PlaywrightTimeoutError as e:
            raise AcsisAutomationError(
                f"Data fiber untuk {no_internet} tidak muncul. "
                "Cek No Internet — mungkin salah / tidak ditemukan.",
                step="search",
            ) from e

        await self._maybe_screenshot(page, "05_fiber_loaded")
        self.on_progress("📊 Data fiber ketemu, mau restart...")
        logger.info("Fiber info termuat untuk %s.", no_internet)

    async def _trigger_restart(self, page: Page, dialogs: list[str]) -> None:
        self.on_progress("⚡ Klik Restart ONT...")
        # Klik menu "Restart ONT" di sidebar kiri.
        await page.get_by_text(re.compile(r"^Restart ONT$", re.I)).first.click()
        await self._maybe_screenshot(page, "06_restart_clicked")

        # Tunggu sampai minimal 2 dialog (konfirmasi + hasil) muncul.
        # Batas waktu aman: 30 detik.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if any("Berhasil" in d or "Gagal" in d for d in dialogs):
                break
            await asyncio.sleep(0.5)
        else:
            raise AcsisAutomationError(
                "Tidak menerima pop-up hasil restart dalam 30 detik.",
                step="restart",
            )

    def _interpret(
        self, no_internet: str, dialogs: list[str], duration: float
    ) -> RestartResult:
        success = any(re.search(r"Berhasil", d, re.I) for d in dialogs)
        if success:
            msg = f"ONT {no_internet} berhasil di-restart."
        else:
            joined = " | ".join(dialogs) or "(tidak ada dialog)"
            msg = f"Status akhir tidak menentu. Dialog: {joined}"
        return RestartResult(
            success=success,
            message=msg,
            no_internet=no_internet,
            duration_sec=round(duration, 2),
            dialogs_seen=dialogs,
        )

    async def _maybe_screenshot(self, page: Page, label: str) -> None:
        if not self.debug_dir:
            return
        try:
            os.makedirs(self.debug_dir, exist_ok=True)
            path = os.path.join(self.debug_dir, f"{label}.png")
            await page.screenshot(path=path, full_page=True)
        except Exception:  # noqa: BLE001
            logger.exception("Gagal simpan screenshot %s", label)
