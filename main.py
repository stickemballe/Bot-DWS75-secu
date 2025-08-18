import os
import telebot
import config
import time
import requests
import random
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS

from security import verify_turnstile, save_user_verification, is_verification_valid, is_flooding
from handlers.menus import menu_principal_keyboard, verification_keyboard, infoscommande_keyboard, contacts_keyboard, liens_keyboard

bot = telebot.TeleBot(config.BOT_TOKEN)
app = Flask('')
allowed_origins = ["https://www.dws75shop.com", "https://dws75shop.com"]
CORS(app, resources={r"/webapp/*": {"origins": allowed_origins}})

short_code_storage = {}

@app.route('/webapp/get-short-code', methods=['POST'])
def get_short_code():
    data = request.json
    turnstile_token = data.get('token')
    user_id = data.get('user_id')

    if not all([turnstile_token, user_id]):
        return jsonify({"ok": False, "error": "Données manquantes"}), 400

    if not verify_turnstile(turnstile_token):
        return jsonify({"ok": False, "error": "Captcha invalide"}), 403

    while True:
        code = str(random.randint(100000, 999999))
        if code not in short_code_storage: break
    
    short_code_storage[code] = {"user_id": user_id, "expires": time.time() + 300}
    config.logger.info(f"Code court {code} généré pour l'utilisateur {user_id}.")
    return jsonify({"ok": True, "short_code": code})

@app.route('/')
def home():
    return "Bot et API de session actifs."

@bot.message_handler(commands=['start', 'menu'])
def command_start(message):
    user_id = message.from_user.id
    if is_flooding(user_id): return

    if is_verification_valid(user_id):
        send_welcome_message(message.chat.id, user_id)
    else:
        texte_prompt = "🔒 **Bienvenue !**\n\nPour accéder au bot, une vérification rapide est nécessaire."
        bot.send_message(message.chat.id, texte_prompt, reply_markup=verification_keyboard())

@bot.message_handler(commands=['aide'])
def command_aide(message):
    user_id = message.from_user.id
    if is_flooding(user_id): return

    texte_aide = (
        "❓ **Mode d'emploi du bot** ❓\n\n"
        "Bienvenue ! Voici comment utiliser notre service pour accéder à la boutique en toute sécurité.\n\n"
        "**1. La Vérification (une seule fois par semaine)**\n"
        "Pour éviter les robots, nous demandons une simple vérification :\n"
        "   • Cliquez sur le bouton `✅ Me Vérifier Maintenant`.\n"
        "   • Une fenêtre s'ouvrira pour résoudre un captcha.\n"
        "   • Un **code à 6 chiffres** vous sera montré.\n"
        "   • Retournez au chat et **envoyez simplement ce code** pour débloquer le bot.\n\n"
        "**2. Le Menu Principal**\n"
        "Une fois vérifié, vous aurez accès à toutes
