import os
import time
import random
import re
import logging
import requests
from telebot import TeleBot

# === Config depuis Railway ===
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CAPTCHA_KEY = os.getenv("CAPTCHA_KEY")
CAPTCHA_SECRET = os.getenv("CAPTCHA_SECRET")

# === Système de logs ===
logging.basicConfig(
    filename="security.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === Données utilisateurs ===
user_infractions = {}
blacklist = set()
captcha_pending = {}

# === Paramètres sécurité ===
SPAM_INTERVAL = 3  # secondes
MAX_INFRACTIONS = 5
OFFENSIVE_WORDS = ["spam", "arnaque", "escroc"]
LINK_PATTERN = re.compile(r"(https?://\S+|t\.me/\S+)", re.IGNORECASE)

# === Génération captcha simple ===
def generate_captcha(user_id):
    a, b = random.randint(1, 9), random.randint(1, 9)
    captcha_pending[user_id] = {"question": f"{a} + {b}", "answer": str(a + b)}
    return captcha_pending[user_id]["question"]

# === Vérification captcha ===
def validate_captcha(bot: TeleBot, message):
    uid = message.from_user.id
    if uid in captcha_pending:
        if message.text.strip() == captcha_pending[uid]["answer"]:
            del captcha_pending[uid]
            bot.send_message(uid, "✅ Captcha validé ! Bienvenue.")
            return True
        else:
            bot.send_message(uid, "❌ Mauvaise réponse, réessayez : " + captcha_pending[uid]["question"])
            return False
    return True

# === Vérification sécurité globale ===
def check_security(bot: TeleBot, message):
    uid = message.from_user.id
    now = time.time()

    # Bloqué si blacklist
    if uid in blacklist:
        bot.send_message(uid, "🚫 Vous êtes bloqué.")
        return False

    # Vérif captcha
    if uid in captcha_pending:
        bot.send_message(uid, "🔐 Veuillez résoudre le captcha : " + captcha_pending[uid]["question"])
        return False

    # Anti-spam
    last_time = user_infractions.get(uid, {}).get("last_time", 0)
    if now - last_time < SPAM_INTERVAL:
        add_infraction(uid, bot, "Spam détecté")
        return False

    # Filtrage contenu
    text = (message.text or "").lower()
    if LINK_PATTERN.search(text) or any(word in text for word in OFFENSIVE_WORDS):
        add_infraction(uid, bot, "Contenu interdit")
        return False

    # Mise à jour dernier message + garantie de la clé 'count'
    store = user_infractions.setdefault(uid, {})
    store["last_time"] = now
    if "count" not in store:
        store["count"] = 0
    return True

# === Ajouter une infraction ===
def add_infraction(uid, bot: TeleBot, reason):
    data = user_infractions.setdefault(uid, {})
    data["count"] = data.get("count", 0) + 1  # sécurise l'incrément
    user_infractions[uid] = data

    logging.warning(f"Infraction {reason} pour utilisateur {uid}")

    if uid == ADMIN_ID:
        return

    if data["count"] >= MAX_INFRACTIONS:
        blacklist.add(uid)
        bot.send_message(uid, "🚫 Trop d'infractions, vous êtes bloqué.")
        bot.send_message(ADMIN_ID, f"🚨 Utilisateur {uid} blacklisté ({reason})")
