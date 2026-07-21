"""
GuessTheAnime_BOT
==================
A Telegram bot that identifies anime from screenshots using trace.moe
for scene-matching and AniList for metadata enrichment.

Run directly:  python bot.py
Deploy on Render.com as a "Background Worker" (see README.md).
"""

import asyncio
import logging
import os
import random
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReactionTypeEmoji,
    BufferedInputFile,
)
from dotenv import load_dotenv

import storage
from anime_lookup import identify_scene, fetch_anilist_details, LookupError
from formatting import (
    START_MESSAGE,
    HELP_MESSAGE,
    anime_result_caption,
    admin_panel_message,
    ADMIN_USERNAME,
)

# --------------------------------------------------------------- config ----
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "834450011"))
MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "20"))

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("guesstheanime.bot")

# Only these emojis are ever used to react to a submitted image.
ALLOWED_REACTIONS = [
    "❤️", "🧡", "💛", "💚", "🩵", "💙", "💜", "🩷", "🤍", "💖",
    "💝", "💗", "💓", "💞", "💕", "♥️", "❣️", "💟", "❤️‍🩹", "❤️‍🔥",
]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# --------------------------------------------------------- simple anti-spam
_last_request: dict[int, float] = defaultdict(float)
SPAM_COOLDOWN_SECONDS = 4


def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    if now - _last_request[user_id] < SPAM_COOLDOWN_SECONDS:
        return True
    _last_request[user_id] = now
    return False


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ------------------------------------------------------------- FSM states --
class BroadcastState(StatesGroup):
    waiting_for_message = State()


# ------------------------------------------------------------ keyboards ----
def result_keyboard(anilist_url: str | None) -> InlineKeyboardMarkup:
    buttons = []
    if anilist_url:
        buttons.append(InlineKeyboardButton(text="ℹ️ More Info", url=anilist_url))
    buttons.append(InlineKeyboardButton(text="🔄 Search Again", callback_data="search_again"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="👥 Total Users", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="📊 Bot Stats", callback_data="admin_stats"),
                InlineKeyboardButton(text="🧾 Error Logs", callback_data="admin_logs"),
            ],
            [
                InlineKeyboardButton(text="🔴 Disable Bot", callback_data="admin_disable"),
                InlineKeyboardButton(text="🟢 Enable Bot", callback_data="admin_enable"),
            ],
            [
                InlineKeyboardButton(text="♻️ Restart Bot", callback_data="admin_restart"),
            ],
        ]
    )


# ------------------------------------------------------------- middleware --
@router.message.middleware()
async def track_user_middleware(handler, event: Message, data):
    if event.from_user and not event.from_user.is_bot:
        storage.add_user(event.from_user.id, event.from_user.username)
    return await handler(event, data)


@router.message.middleware()
async def maintenance_middleware(handler, event: Message, data):
    if not storage.is_bot_enabled() and event.from_user and event.from_user.id != ADMIN_ID:
        await event.answer(
            "🚧 <b>GuessTheAnime_BOT is temporarily under maintenance.</b>\n"
            "Please check back shortly! 🙏"
        )
        return
    return await handler(event, data)


# ------------------------------------------------------------ /start -------
@router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "there"
    await message.answer(START_MESSAGE.format(name=name))


# ------------------------------------------------------------- /help -------
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_MESSAGE)


# ------------------------------------------------------------ /admin -------
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ This command is restricted to the bot administrator.")
        return
    stats = storage.get_stats()
    await message.answer(
        admin_panel_message(stats, storage.total_users()),
        reply_markup=admin_keyboard(),
    )


# ------------------------------------------------------- admin callbacks ---
@router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Not authorized.", show_alert=True)
        return

    action = callback.data

    if action == "admin_broadcast":
        await callback.message.answer(
            "📢 <b>Broadcast Mode</b>\n\nSend me the message you want to broadcast "
            "to <b>all users</b> now (text, photo, or any message). Type /cancel to abort."
        )
        await state.set_state(BroadcastState.waiting_for_message)
        await callback.answer()

    elif action == "admin_users":
        await callback.message.answer(f"👥 <b>Total Users:</b> {storage.total_users()}")
        await callback.answer()

    elif action == "admin_stats":
        stats = storage.get_stats()
        await callback.message.answer(
            admin_panel_message(stats, storage.total_users()),
            reply_markup=admin_keyboard(),
        )
        await callback.answer()

    elif action == "admin_logs":
        logs = storage.get_logs(15)
        if not logs:
            text = "🧾 No logs recorded yet."
        else:
            text = "🧾 <b>Recent Logs</b>\n\n" + "\n".join(
                f"[{l['time']}] {l['level']}: {l['message']}" for l in logs
            )
        await callback.message.answer(text[:4000])
        await callback.answer()

    elif action == "admin_disable":
        storage.set_bot_enabled(False)
        storage.add_log("Bot disabled by admin", "ADMIN")
        await callback.message.answer("🔴 Bot has been <b>disabled</b>. Users will see a maintenance notice.")
        await callback.answer()

    elif action == "admin_enable":
        storage.set_bot_enabled(True)
        storage.add_log("Bot enabled by admin", "ADMIN")
        await callback.message.answer("🟢 Bot has been <b>enabled</b> and is live again.")
        await callback.answer()

    elif action == "admin_restart":
        await callback.message.answer("♻️ Restart signal received. If running under a process manager "
                                        "(Render/Docker/PM2), the process will now exit and restart.")
        storage.add_log("Manual restart triggered by admin", "ADMIN")
        await callback.answer()
        await bot.session.close()
        os._exit(0)


@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        await state.clear()
        await message.answer("❌ Cancelled.")


@router.message(BroadcastState.waiting_for_message)
async def do_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    users = storage.get_all_users()
    sent, failed = 0, 0
    status_msg = await message.answer(f"📢 Broadcasting to {len(users)} users...")

    for uid in users:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            storage.add_log(f"Broadcast failed for {uid}: {e}", "ERROR")
        await asyncio.sleep(0.05)  # gentle throttle to respect Telegram rate limits

    await status_msg.edit_text(f"✅ Broadcast complete.\nSent: {sent} | Failed: {failed}")
    storage.add_log(f"Broadcast sent by admin — success={sent} failed={failed}", "ADMIN")


# ------------------------------------------------------- search again btn --
@router.callback_query(F.data == "search_again")
async def search_again(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📸 Send me another anime screenshot and I'll identify it!")


# ---------------------------------------------------------- image handler --
@router.message(F.photo | (F.document & F.document.mime_type.startswith("image/")))
async def handle_image(message: Message):
    user_id = message.from_user.id

    if not is_admin(user_id) and is_rate_limited(user_id):
        await message.reply("⏳ You're sending images too quickly — please wait a few seconds and try again.")
        return

    # 1) React with a random allowed heart emoji
    try:
        await message.react([ReactionTypeEmoji(emoji=random.choice(ALLOWED_REACTIONS))])
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not set reaction: %s", e)

    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    processing = await message.reply("🔍 <b>Scanning image...</b> Please wait a moment ⏳")

    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id
            if message.document.file_size and message.document.file_size > MAX_IMAGE_MB * 1024 * 1024:
                raise LookupError(f"Image is larger than {MAX_IMAGE_MB}MB.")

        tg_file = await bot.get_file(file_id)
        file_bytes_io = await bot.download_file(tg_file.file_path)
        image_bytes = file_bytes_io.read()

        trace_result = await identify_scene(image_bytes)
        storage.bump_stat("total_scans")

        anilist_data = None
        search_key = trace_result.get("anilist_id") or trace_result.get("filename")
        if search_key:
            try:
                anilist_data = await fetch_anilist_details(search_key)
            except Exception as e:  # noqa: BLE001
                logger.warning("AniList lookup failed: %s", e)
                storage.add_log(f"AniList lookup failed: {e}", "WARNING")

        caption = anime_result_caption(trace_result, anilist_data)
        keyboard = result_keyboard(anilist_data.get("site_url") if anilist_data else None)

        cover = anilist_data.get("cover_image") if anilist_data else None

        await processing.delete()

        # Send back the same image the user provided, with the formatted caption
        if message.photo:
            await message.reply_photo(message.photo[-1].file_id, caption=caption, reply_markup=keyboard)
        else:
            await message.reply_document(message.document.file_id, caption=caption, reply_markup=keyboard)

        # Bonus: also show the official cover art if it differs from the user's image
        if cover:
            try:
                await message.answer_photo(cover, caption="🖼 Official cover art")
            except Exception:  # noqa: BLE001
                pass

        storage.bump_stat("successful_scans")

    except LookupError as e:
        storage.bump_stat("failed_scans")
        storage.add_log(f"Lookup failed for user {user_id}: {e}", "WARNING")
        await processing.edit_text(
            "😔 <b>No match found.</b>\n\n"
            f"Reason: {e}\n\n"
            "💡 Try a clearer, uncropped screenshot straight from the episode."
        )
    except Exception as e:  # noqa: BLE001
        storage.bump_stat("failed_scans")
        logger.exception("Unexpected error while processing image")
        storage.add_log(f"Unexpected error for user {user_id}: {e}", "ERROR")
        await processing.edit_text(
            "⚠️ Something went wrong while analyzing your image. Please try again in a moment.\n"
            f"If this keeps happening, contact {ADMIN_USERNAME}."
        )


# --------------------------------------------------------- fallback text ---
@router.message(F.text & ~F.text.startswith("/"))
async def fallback_text(message: Message):
    await message.answer(
        "📸 Send me an <b>anime screenshot</b> and I'll identify it for you!\n"
        "Type /help if you need guidance."
    )


# ------------------------------------------------------------------ main ---
async def main():
    if os.getenv("ENABLE_KEEPALIVE", "false").lower() == "true":
        from keep_alive import start_keep_alive
        start_keep_alive()

    storage.add_log("Bot started", "INFO")
    logger.info("GuessTheAnime_BOT starting as @%s ...", (await bot.get_me()).username)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
