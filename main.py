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

# --- COMMANDE /aide CORRIGÉE AVEC TRIPLE GUILLEMETS ---
@bot.message_handler(commands=['aide'])
def command_aide(message):
    user_id = message.from_user.id
    if is_flooding(user_id): return

    texte_aide = """
❓ **Mode d'emploi du bot** ❓

Bienvenue ! Voici comment utiliser notre service pour accéder à la boutique en toute sécurité.

**1. La Vérification (une seule fois par semaine)**
Pour éviter les robots, nous demandons une simple vérification :
   • Cliquez sur le bouton `✅ Me Vérifier Maintenant`.
   • Une fenêtre s'ouvrira pour résoudre un captcha.
   • Un **code à 6 chiffres** vous sera montré.
   • Retournez au chat et **envoyez simplement ce code** pour débloquer le bot.

**2. Le Menu Principal**
Une fois vérifié, vous aurez accès à toutes nos options :
   • `💫 Menu Interactif` : Ouvre notre boutique complète.
   • `ℹ️ Infos & Commande` : Affiche les détails sur nos horaires et modes de livraison.
   • `🛒 Commander` : Ouvre une conversation WhatsApp pour passer votre commande.

En cas de problème, vous pouvez toujours relancer le processus avec la commande /start.
"""
    bot.reply_to(message, texte_aide, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.isdigit() and len(message.text) == 6)
def handle_short_code(message):
    user_id = message.from_user.id
    if is_flooding(user_id): return
    
    code = message.text
    if is_verification_valid(user_id):
        bot.reply_to(message, "✅ Vous êtes déjà vérifié.")
        send_welcome_message(message.chat.id, user_id)
        return

    code_data = short_code_storage.get(code)
    if code_data and time.time() < code_data["expires"] and code_data["user_id"] == user_id:
        del short_code_storage[code]
        save_user_verification(user_id)
        bot.reply_to(message, "✅ **Accès autorisé !**")
        send_welcome_message(message.chat.id, user_id)
    else:
        bot.reply_to(message, "❌ Ce code est incorrect ou a expiré. Veuillez relancer avec /start.")

def send_welcome_message(chat_id: int, user_id: int):
    texte_accueil = "<b><u>🤖 Bienvenue sur le Bot DWS75 🤖</u></b>\n\nVous avez maintenant accès à toutes les fonctionnalités."
    try:
        bot.send_photo(chat_id, config.IMAGE_ACCUEIL_URL, caption=texte_accueil, parse_mode='HTML', reply_markup=menu_principal_keyboard(user_id))
    except Exception as e:
        config.logger.error(f"Impossible d'envoyer le message de bienvenue à {chat_id}: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if is_flooding(user_id): return
    
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    if not is_verification_valid(user_id):
        bot.answer_callback_query(call.id, "Veuillez d'abord vous vérifier avec /start.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    data = call.data

    if data == "menu_principal":
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            config.logger.warning(f"Impossible de supprimer le message pour le retour au menu: {e}")
        send_welcome_message(chat_id, user_id)

    elif data == "submenu_infoscommande":
        texte_infos = (
            "<b><u>ℹ️ Prise de commandes & Livraison</u></b>\n\n"
            "Les commandes se font via <b>WhatsApp Standard</b> de 10h à 19h.\n"
            "Les précommandes pour le lendemain débutent à 20h.\n\n"
            "<b><u>🚚 Horaires des tournées (7j/7) :</u></b>\n"
            "    • <b>Première :</b> départ à 12h30\n"
            "    • <b>Deuxième :</b> départ à 15h30\n"
            "    • <b>Troisième :</b> départ à 18h30\n\n"
            "Une <b>quatrième tournée</b> (départ 20h) est ajoutée le vendredi et le samedi.\n\n"
            "Nous livrons dans toute l'<b>Île-de-France</b> pour toute commande de 120€ ou plus.\n\n"
            "<b><u>📍 Meet-up (remise en main propre) :</u></b>\n"
            "Minimum de commande de 50€.\n\n"
            "<b><u>🆘 Service Après-Vente (S.A.V) :</u></b>\n"
            "Pour toute réclamation, contactez le +33 6 20 83 26 23.\n\n"
            "Merci de votre confiance ! 🏆"
        )
        bot.edit_message_caption(caption=texte_infos, chat_id=chat_id, message_id=message_id, reply_markup=infoscommande_keyboard(), parse_mode='HTML')

    elif data == "submenu_contacts":
        texte_contacts = "<b><u>☎️ Contacts ☎️</u></b>\n\nPour toutes questions ou assistance, contactez-nous via WhatsApp :"
        bot.edit_message_caption(caption=texte_contacts, chat_id=chat_id, message_id=message_id, reply_markup=contacts_keyboard(), parse_mode='HTML')

    elif data == "submenu_liens":
        texte_liens = "<b><u>🌐 Liens Utiles 🌐</u></b>\n\nRetrouvez nos liens importants ci-dessous :"
        bot.edit_message_caption(caption=texte_liens, chat_id=chat_id, message_id=message_id, reply_markup=liens_keyboard(), parse_mode='HTML')

    else:
        bot.answer_callback_query(call.id, "Fonction en cours de développement.", show_alert=True)

# --- Lancement ---
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    while True:
        try:
            config.logger.info("Bot en cours de démarrage...")
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            config.logger.error(f"Erreur polling: {e}. Redémarrage dans 15s...")
            time.sleep(15)

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    run_bot()
