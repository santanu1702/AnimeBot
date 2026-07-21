"""
formatting.py
All user-facing text lives here so tone/wording can be tweaked without
touching bot logic.
"""

import time

ADMIN_USERNAME = "@PRIMExOFCL"

START_MESSAGE = """
✨ <b>Welcome to GuessTheAnime_BOT!</b> ✨

Hey there, {name}! 👋 I'm your personal <b>anime detective</b> 🕵️‍♂️🎬 —
send me literally <i>any</i> anime screenshot and I'll tell you exactly
what it's from, in seconds.

━━━━━━━━━━━━━━━━━━━━
🔍 <b>What I can do</b>
━━━━━━━━━━━━━━━━━━━━
🖼 Identify the anime from a single screenshot
🎭 Detect the character (when available)
📊 Show similarity/confidence score
⭐ Pull ratings, episode count &amp; release info
⚡ Reply in just a few seconds

━━━━━━━━━━━━━━━━━━━━
📩 <b>How to use me</b>
━━━━━━━━━━━━━━━━━━━━
1️⃣ Find any anime screenshot (from an episode, MAL, Pinterest, etc.)
2️⃣ Send it to me directly in this chat
3️⃣ I'll react with a random ❤️ and start scanning
4️⃣ Sit back — your results arrive in seconds!

━━━━━━━━━━━━━━━━━━━━
💡 <b>Pro tip:</b> Clear, uncropped screenshots give the most accurate matches!

Type /help for detailed usage tips, or just send an image right now to try it out 🚀
"""

HELP_MESSAGE = """
❓ <b>GuessTheAnime_BOT — Help Center</b>

━━━━━━━━━━━━━━━━━━━━
⚙️ <b>How it works</b>
━━━━━━━━━━━━━━━━━━━━
I use frame-matching AI (via trace.moe) to compare your screenshot against
millions of anime frames, then enrich the match with metadata from AniList —
titles, episode counts, ratings, and release info.

━━━━━━━━━━━━━━━━━━━━
🖼 <b>Supported formats</b>
━━━━━━━━━━━━━━━━━━━━
• JPG / JPEG
• PNG
• WEBP
• Compressed Telegram photos &amp; uncompressed documents

━━━━━━━━━━━━━━━━━━━━
🎯 <b>Accuracy &amp; limitations</b>
━━━━━━━━━━━━━━━━━━━━
• Works best on actual anime screenshots (not fan art or edits)
• Heavily cropped, blurry, or upscaled images reduce accuracy
• Watermarks/text overlays can lower the similarity score
• Very obscure or unlicensed titles may not be indexed

━━━━━━━━━━━━━━━━━━━━
💡 <b>Tips for best results</b>
━━━━━━━━━━━━━━━━━━━━
✅ Use a clear, unedited frame straight from the episode
✅ Avoid collages — one scene per image works best
✅ Higher resolution = better matching
✅ If a scan fails, try a slightly different frame from the same scene

━━━━━━━━━━━━━━━━━━━━
🙏 <b>Credits</b>
━━━━━━━━━━━━━━━━━━━━
• Scene recognition: trace.moe
• Anime metadata: AniList.co
• Built &amp; maintained by {admin}

━━━━━━━━━━━━━━━━━━━━
📬 <b>Need help?</b>
━━━━━━━━━━━━━━━━━━━━
Contact the admin: {admin}
""".format(admin=ADMIN_USERNAME)


def anime_result_caption(trace_result: dict, anilist: dict | None, character_name: str | None = None) -> str:
    similarity = trace_result.get("similarity", 0)

    if anilist:
        name_romaji = anilist.get("title_romaji") or "Unknown"
        name_english = anilist.get("title_english")
        anime_name = name_romaji if not name_english or name_english == name_romaji else f"{name_romaji} ({name_english})"
        episodes = anilist.get("episodes", "Unknown")
        seasons = anilist.get("estimated_seasons", "Unknown")
        release_date = anilist.get("release_date", "Unknown")
        rating = anilist.get("rating", "N/A")
    else:
        anime_name = trace_result.get("filename") or "Unknown"
        episodes = "Unknown"
        seasons = "Unknown"
        release_date = "Unknown"
        rating = "N/A"

    episode_no = trace_result.get("episode")
    timestamp = None
    if trace_result.get("from_time") is not None:
        timestamp = f"{_fmt_time(trace_result['from_time'])} → {_fmt_time(trace_result['to_time'])}"

    lines = [
        "🎬 <b>Anime Identified!</b>",
        "",
        f"📌 <b>Character Name:</b> {character_name or 'Not detected'}",
        f"📌 <b>Anime Name:</b> {anime_name}",
        "📌 <b>Language:</b> Japanese (original)",
        f"📌 <b>Total Seasons:</b> {seasons}",
        f"📌 <b>Total Episodes:</b> {episodes}",
        f"📌 <b>Release Date:</b> {release_date}",
        f"📌 <b>Anime Rating:</b> {rating}",
        f"📌 <b>Similarity:</b> {similarity}%",
    ]

    if episode_no:
        lines.append(f"📺 <b>Matched Episode:</b> {episode_no}")
    if timestamp:
        lines.append(f"⏱ <b>Timestamp:</b> {timestamp}")

    lines.append("")
    lines.append("✨ <i>Powered by trace.moe &amp; AniList</i>")

    return "\n".join(lines)


def _fmt_time(seconds: float) -> str:
    seconds = int(seconds or 0)
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def admin_panel_message(stats: dict, total_users: int) -> str:
    uptime = time.time() - stats.get("started_at", time.time())
    return (
        "🛠 <b>Admin Control Panel</b>\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"🔍 Total Scans: <b>{stats.get('total_scans', 0)}</b>\n"
        f"✅ Successful: <b>{stats.get('successful_scans', 0)}</b>\n"
        f"❌ Failed: <b>{stats.get('failed_scans', 0)}</b>\n"
        f"⏱ Uptime: <b>{_fmt_uptime(uptime)}</b>\n"
        f"🔌 Bot Status: <b>{'🟢 Enabled' if stats.get('bot_enabled', True) else '🔴 Disabled'}</b>\n\n"
        "Choose an action below 👇"
    )


def _fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)
