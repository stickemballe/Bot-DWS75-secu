import os
import telebot
import config
import time
import requests
import random
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS

from security import verify_turnstile, save_user_verification, is_verification_valid
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
    if is_verification_valid(user_id):
        send_welcome_message(message.chat.id, user_id)
    else:
        texte_prompt = "🔒 **Bienvenue !**\n\nPour accéder au bot, une vérification rapide est nécessaire."
        bot.send_message(message.chat.id, texte_prompt, reply_markup=verification_keyboard())

@bot.message_handler(func=lambda message: message.text and message.text.isdigit() and len(message.text) == 6)
def handle_short_code(message):
    user_id = message.from_user.id
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

# --- GESTIONNAIRE DES BOUTONS (CALLBACKS) MIS À JOUR ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id

    if not is_verification_valid(user_id):
        bot.answer_callback_query(call.id, "Veuillez d'abord vous vérifier avec /start.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    data = call.data

    if data == "menu_principal":
        # Pour retourner au menu principal, on renvoie le message d'accueil
        # Il est préférable de supprimer l'ancien message et d'en envoyer un nouveau
        # car on ne peut pas "ré-ajouter" une photo qui a été modifiée.
        bot.delete_message(chat_id, message_id)
        send_welcome_message(chat_id, user_id)

    elif data == "submenu_infoscommande":
        texte_infos = (
            "<b><u>ℹ️ Les prises de commandes</u></b> se font uniquement sur le WhatsApp standard de <i>10h à 19h</i>, les précommandes se font à partir de 20h pour le lendemain.\n\n"
            "🚚 <b><u>Livraison :</u></b> horaires des tournée de livraison 7j/7\n\n"
            "🕧 <b><u>Première</u></b> ➡️ Départs 12h30\n"
            "🕞 <b><u>Deuxième</u></b> ➡️ Départs 15h30\n"
            "🕕 <b><u>Troisième</u></b> ➡️ Départs 18h30\n\n"
            "<b>Le vendredi et samedi</b> ➡️ <b><u>4ème tournée</u></b>, départs 20H00 🕗\n\n"
            "🚚Nous livrons <b><u>toute île de France à partir de 120€ de commande</u></b> 🛒\n"
            "____________________________________________\n\n"
            "📍 <b><u>Meet-up</u></b> / Remise en main propre à une adresse discrète, en privé ➡️ Minimum de commande : <b><u>50€</u></b> 🛒\n\n"
            "🚨<b><u>WhatsApp S.A.V</u></b> 🚨\n"
            "+33 6 20 83 26 23\n"
            "Pour toute réclamation (problèmes sur le produit, produits oubliés, problème avec un livreur...)\n\n"
            "Merci de votre confiance et à bientôt ! 🏆"
        )
        # On modifie la légende de la photo existante
        bot.edit_message_caption(caption=texte_infos, chat_id=chat_id, message_id=message_id, reply_markup=infoscommande_keyboard(), parse_mode='HTML')

    elif data == "submenu_contacts":
        texte_contacts = (
            "<b><u>☎️ Contacts ☎️</u></b>\n\n"
            "Pour toutes questions ou assistance, contactez-nous via WhatsApp :"
        )
        bot.edit_message_caption(caption=texte_contacts, chat_id=chat_id, message_id=message_id, reply_markup=contacts_keyboard(), parse_mode='HTML')

    elif data == "submenu_liens":
        texte_liens = (
            "<b><u>🌐 Liens Utiles 🌐</u></b>\n\n"
            "Retrouvez nos liens importants ci-dessous :"
        )
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