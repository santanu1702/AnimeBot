"""
keep_alive.py
Tiny Flask server exposing a "/" health-check endpoint so a free
UptimeRobot (or Render health check) monitor can ping the service and
keep it from spinning down.

Only needed if you deploy the bot as a Web Service on Render. If you
deploy it as a Background Worker instead, you don't need this file —
background workers don't sleep due to inactivity.
"""

import threading
from flask import Flask

app = Flask(__name__)


@app.route("/")
def health_check():
    return {"status": "ok", "bot": "GuessTheAnime_BOT"}, 200


def run():
    app.run(host="0.0.0.0", port=8080)


def start_keep_alive():
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
