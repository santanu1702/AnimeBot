# 🤖 GuessTheAnime_BOT

A Telegram bot that identifies anime from screenshots using **trace.moe**
(scene matching) + **AniList** (metadata: titles, episodes, ratings, dates),
reacts to submitted images with a random ❤️-family emoji, and includes a
full admin control panel.

Admin: **@PRIMExOFCL** (ID `834450011`)

---

## ✨ Features

- Detects anime from any screenshot sent to the bot
- Reacts to every image using a random emoji from an approved heart set
- Sends the original image back with a clean, formatted result:
  character (if detectable), anime name (original + English), language,
  seasons, episodes, release date, rating, similarity %
- Inline buttons: **More Info** (AniList page) / **Search Again**
- `/start` and `/help` with rich, styled explanations
- Admin panel (`/admin`, admin-only):
  - 📢 Broadcast a message to all users
  - 👥 View total users
  - 📊 Bot stats (scans, success/fail counts, uptime)
  - 🧾 View recent error/API logs
  - 🔴/🟢 Enable / disable the bot (maintenance mode)
  - ♻️ Restart the bot process
- Basic anti-spam cooldown per user
- JSON-file persistence (no external DB required)
- Ready for Render.com, with optional keep-alive HTTP endpoint for
  UptimeRobot

---

## 📦 Project structure

```
guesstheanime_bot/
├── bot.py              # main entrypoint & handlers
├── anime_lookup.py      # trace.moe + AniList API wrappers
├── formatting.py         # all user-facing text/templates
├── storage.py             # JSON-file persistence (users/stats/logs)
├── keep_alive.py           # optional Flask health-check server
├── requirements.txt
├── .env.example
├── Procfile              # for Render/Heroku-style process declaration
├── render.yaml            # Render.com Blueprint (one-click deploy)
└── README.md
```

---

## 🚀 Local setup

1. **Clone / unzip** this project and `cd` into it.

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create your bot with [@BotFather](https://t.me/BotFather)** and copy
   the token it gives you.

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env`:
   ```env
   BOT_TOKEN=123456789:AA...your-real-token
   ADMIN_ID=834450011
   MAX_IMAGE_MB=20
   ```

6. **Enable Telegram message content privacy** (optional but recommended):
   In BotFather → `/mybots` → your bot → **Bot Settings → Group Privacy**
   → leave enabled unless you want it reading all group messages.

7. **Run it:**
   ```bash
   python bot.py
   ```
   You should see a log line confirming the bot started polling.

8. Open a chat with your bot on Telegram and send `/start`.

---

## ☁️ Deploying on Render.com

### Option A — One-click Blueprint

1. Push this project to a **GitHub repository**.
2. On Render, choose **New → Blueprint**, and point it at your repo.
   Render will read `render.yaml` automatically.
3. When prompted, fill in the `BOT_TOKEN` environment variable (marked
   `sync: false` so it's entered securely in the dashboard, never
   committed to git).
4. Deploy. Render will run `pip install -r requirements.txt` then
   `python bot.py` as a **Background Worker** — polling bots don't need
   a public HTTP port, so this is the correct service type.

### Option B — Manual setup

1. **New → Background Worker** on Render.
2. Connect your GitHub repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `python bot.py`
5. Add environment variables under **Environment**:
   - `BOT_TOKEN` = your real token
   - `ADMIN_ID` = `834450011`
   - `MAX_IMAGE_MB` = `20`
6. Deploy.

> Background Workers on Render don't sleep from inactivity (that only
> affects free **Web Services**), so this is the most reliable free-tier
> option for a long-polling Telegram bot.

### Option C — Deploy as a Web Service (if you need a public URL)

If your Render plan only offers Web Services, set `ENABLE_KEEPALIVE=true`
in your environment variables. This starts a tiny Flask server on port
`8080` alongside the bot so Render's health checks (and UptimeRobot) have
something to ping at `/`.

---

## ⏱ Keeping it 24/7 with UptimeRobot

Only needed if deployed as a **Web Service** with `ENABLE_KEEPALIVE=true`:

1. Go to [UptimeRobot](https://uptimerobot.com) → **Add New Monitor**.
2. Monitor type: **HTTP(s)**.
3. URL: your Render service's public URL (e.g. `https://your-bot.onrender.com/`).
4. Interval: every 5 minutes.

Background Workers don't need this step at all.

---

## 🔐 Admin panel usage

Only the Telegram account with ID `834450011` (@PRIMExOFCL) can use
these:

| Command | Description |
|---|---|
| `/admin` | Opens the admin control panel with inline buttons |

From the panel you can broadcast messages, check total users, view live
stats (scans/uptime), read recent error logs, toggle maintenance mode,
or restart the process. All admin actions are logged.

---

## 🧠 How anime detection works

1. User sends a photo (or an image file) to the bot.
2. The bot reacts with a random emoji from the approved heart set.
3. The raw image bytes are sent to **trace.moe**, which returns the
   best-matching anime scene + similarity score.
4. The bot queries **AniList's GraphQL API** using the matched title/ID
   to pull in rich metadata (English/Romaji/Native titles, episode
   count, score, release date, cover art).
5. Everything is formatted into a single clean caption and sent back
   alongside the user's original image, with inline buttons for more
   info or to search again.

> Note: trace.moe identifies **scenes**, not individual characters by
> face. Character name recognition is best-effort — if trace.moe's
> match doesn't clearly imply a character, the bot reports
> "Not detected" rather than guessing.

---

## ⚠️ Limitations

- Free trace.moe usage is rate-limited; very high traffic may need a
  paid API key (see their docs) — swap it into `anime_lookup.py`.
- Season counts are estimated from AniList's prequel/sequel relations
  since AniList doesn't store an explicit "season number" field.
- Fan art, edited images, or non-anime screenshots will not match.

---

## 🙋 Support

Questions or issues? Contact **@PRIMExOFCL** on Telegram.
