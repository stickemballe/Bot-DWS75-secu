# security.py
import time
import re
import random
from telebot import TeleBot

# === CONFIG ===
ADMIN_ID = 6399411185  # Ton ID admin
BANNED_KEYWORDS = ["escroc", "arnaque", "fuck", "pute", "merde"]  # Mots interdits
MAX_INFRACTIONS = 5  # Après combien d'infractions un utilisateur est banni
ANTI_SPAM_DELAY = 3  # En secondes

# === STOCKAGE ===
verified_users = set()
last_message_time = {}
user_infractions = {}
blacklisted_users = set()

# === CAPTCHA ===
def send_captcha(bot: TeleBot, message):
    a, b = random.randint(1, 9), random.randint(1, 9)
    correct = a + b
    bot.send_message(message.chat.id, f"🔐 Veuillez résoudre : {a} + {b} = ?")
    user_infractions[message.from_user.id] = {
        "captcha_answer": correct,
        "count": 0
    }

def validate_captcha(bot: TeleBot, message):
    try:
        if int(message.text) == user_infractions[message.from_user.id]["captcha_answer"]:
            verified_users.add(message.from_user.id)
            bot.send_message(message.chat.id, "✅ Captcha validé ! Bienvenue.")
            return True
    except:
        pass
    bot.send_message(message.chat.id, "❌ Mauvaise réponse. Réessayez.")
    send_captcha(bot, message)
    return False

# === CONTENU INTERDIT ===
def contains_prohibited_content(text):
    if not text:
        return False
    if re.search(r"http[s]?://", text):  # Liens externes
        return True
    if sum(c in "😀😁😂🤣😅😆😉😊😍😘🥰🤩😎🤪" for c in text) > 10:  # Trop d'émojis
        return True
    if any(word in text.lower() for word in BANNED_KEYWORDS):  # Mots interdits
        return True
    return False

# === INFRACTIONS & BAN ===
def register_infraction(bot, user_id, reason, message):
    count = user_infractions.get(user_id, {}).get("count", 0) + 1
    user_infractions[user_id] = {
        "count": count
    }
    bot.send_message(ADMIN_ID, f"⚠️ Infraction de {user_id} : {reason} ({count}/{MAX_INFRACTIONS})")
    if count >= MAX_INFRACTIONS:
        blacklisted_users.add(user_id)
        bot.send_message(ADMIN_ID, f"🚫 Utilisateur {user_id} banni automatiquement.")
        bot.send_message(message.chat.id, "🚫 Vous êtes banni.")

# === CONTROLE GLOBAL ===
def check_security(bot: TeleBot, message):
    user_id = message.from_user.id

    # Si banni
    if user_id in blacklisted_users:
        bot.reply_to(message, "🚫 Vous êtes banni.")
        return False

    # Captcha
    if user_id not in verified_users:
        send_captcha(bot, message)
        return False

    # Anti-spam
    now = time.time()
    if user_id in last_message_time and now - last_message_time[user_id] < ANTI_SPAM_DELAY:
        register_infraction(bot, user_id, "Spam", message)
        return False
    last_message_time[user_id] = now

    # Filtrage
    if contains_prohibited_content(message.text):
        register_infraction(bot, user_id, "Contenu interdit", message)
        return False

    return True
