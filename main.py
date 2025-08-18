import os
import telebot
import config
import time
import requests
import random
from threading import Thread, Timer
from flask import Flask, request, jsonify
from flask_cors import CORS
from html import escape

from security import verify_turnstile, save_user_verification, is_verification_valid, is_flooding
from handlers.menus import menu_principal_keyboard, verification_keyboard, infoscommande_keyboard, contacts_keyboard, liens_keyboard

bot = telebot.TeleBot(config.BOT_TOKEN)
app = Flask('')
allowed_origins = ["https://www.dws75shop.com", "https://dws75shop.com"]
CORS(app, resources={r"/webapp/*": {"origins": allowed_origins}})

# --- Mémoire locale des messages envoyés par le bot (pour les effacer ensuite)
#     Clé = chat_id, Valeur = liste d'IDs de messages envoyés par le bot
_SENT_BY_BOT = {}
_MAX_TRACKED = 10  # on garde une petite file pour sécurité

def _remember_sent(chat_id: int, message_id: int):
    lst = _SENT_BY_BOT.get(chat_id, [])
    lst.append(message_id)
    if len(lst) > _MAX_TRACKED:
        lst = lst[-_MAX_TRACKED:]
    _SENT_BY_BOT[chat_id] = lst

def clear_chat_messages(chat_id: int):
    """Supprime les anciens messages envoyés par le bot dans ce chat (ignore les erreurs)."""
    lst = _SENT_BY_BOT.get(chat_id, [])
    if not lst:
        return
    for mid in lst:
        try:
            bot.delete_message(chat_id, mid)
        except Exception:
            pass
    _SENT_BY_BOT[chat_id] = []

def send_clean_message(chat_id: int, text: str, **kwargs):
    """Efface les anciens messages du bot puis envoie un nouveau message texte."""
    clear_chat_messages(chat_id)
    msg = bot.send_message(chat_id, text, **kwargs)
    _remember_sent(chat_id, msg.message_id)
    return msg

def send_clean_photo(chat_id: int, photo, **kwargs):
    """Efface les anciens messages du bot puis envoie une nouvelle photo (avec caption éventuelle)."""
    clear_chat_messages(chat_id)
    msg = bot.send_photo(chat_id, photo, **kwargs)
    _remember_sent(chat_id, msg.message_id)
    return msg

def send_ephemeral(chat_id: int, text: str, ttl: int = 3, **kwargs):
    """
    Envoie un petit message temporaire qui s'auto-supprime après ttl secondes.
    N'entre pas dans la pile 'clean' pour ne pas être effacé immédiatement.
    """
    msg = bot.send_message(chat_id, text, **kwargs)
    def _del():
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
    Timer(ttl, _del).start()
    return msg

def _display_name_from_message(message) -> str:
    raw = (getattr(message.from_user, "first_name", None)
           or getattr(message.from_user, "username", None)
           or "toi")
    return escape(raw)

def _display_name_from_id(user_id: int) -> str:
    try:
        chat = bot.get_chat(user_id)
        raw = getattr(chat, "first_name", None) or getattr(chat, "username", None) or "toi"
    except Exception:
        raw = "toi"
    return escape(raw)

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
        if code not in short_code_storage:
            break

    short_code_storage[code] = {"user_id": user_id, "expires": time.time() + 300}
    config.logger.info(f"Code court {code} généré pour l'utilisateur {user_id}.")
    return jsonify({"ok": True, "short_code": code})

@app.route('/')
def home():
    return "Bot et API de session actifs."

@bot.message_handler(commands=['start', 'menu'])
def command_start(message):
    user_id = message.from_user.id
    if is_flooding(user_id):
        return

    name = _display_name_from_message(message)

    if is_verification_valid(user_id):
        send_welcome_message(message.chat.id, user_id)
    else:
        texte_prompt = (
            f"🔒 <b>Bienvenue, {name} !</b>\n\n"
            "Pour accéder au bot, une vérification rapide est nécessaire.\n\n"
            "Appuie sur le bouton ci-dessous pour lancer la vérification."
        )
        # On nettoie puis on affiche uniquement le prompt de vérif
        send_clean_message(message.chat.id, texte_prompt, reply_markup=verification_keyboard(), parse_mode='HTML')

@bot.message_handler(commands=['aide'])
def command_aide(message):
    user_id = message.from_user.id
    if is_flooding(user_id):
        return

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
    # On remplace l'écran courant par l'aide (pas de pile de messages)
    send_clean_message(message.chat.id, texte_aide, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.isdigit() and len(message.text) == 6)
def handle_short_code(message):
    user_id = message.from_user.id
    if is_flooding(user_id):
        return

    code = message.text

    if is_verification_valid(user_id):
        # Pas de message "déjà vérifié" pour éviter le bruit : on montre directement l'écran principal
        send_welcome_message(message.chat.id, user_id)
        return

    code_data = short_code_storage.get(code)
    if code_data and time.time() < code_data["expires"] and str(code_data["user_id"]) == str(user_id):
        del short_code_storage[code]
        save_user_verification(user_id)

        # 🔔 Message de succès (éphémère 3s), personnalisé avec le prénom/pseudo
        name = _display_name_from_message(message)
        send_ephemeral(
            message.chat.id,
            f"✅ <b>Vérification réussie, {name} !</b>",
            ttl=3,
            parse_mode='HTML'
        )

        # Puis on affiche l'écran d'accueil propre (image + menu)
        send_welcome_message(message.chat.id, user_id)
        return
    else:
        # On remplace l'écran courant par l'erreur (pour éviter l’empilement)
        send_clean_message(message.chat.id, "❌ Ce code est incorrect ou a expiré. Veuillez relancer avec /start.")

def send_welcome_message(chat_id: int, user_id: int):
    name = _display_name_from_id(user_id)
    texte_accueil = (
        f"<b><u>🤖 Bienvenue, {name} ! 🤖</u></b>\n\n"
        "Vous avez maintenant accès à toutes les fonctionnalités."
    )
    try:
        # On remplace l’écran courant par l’image d’accueil + menu
        send_clean_photo(
            chat_id,
            config.IMAGE_ACCUEIL_URL,
            caption=texte_accueil,
            parse_mode='HTML',
            reply_markup=menu_principal_keyboard(user_id)
        )
    except Exception as e:
        config.logger.error(f"Impossible d'envoyer le message de bienvenue à {chat_id}: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if is_flooding(user_id):
        return

    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not is_verification_valid(user_id):
        bot.answer_callback_query(call.id, "Veuillez d'abord vous vérifier avec /start.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    data = call.data

    if data == "menu_principal":
        # On supprime explicitement le message actuel (si possible), puis on affiche l'accueil propre
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            config.logger.warning(f"Impossible de supprimer le message pour le retour au menu: {e}")
        send_welcome_message(chat_id, user_id)

    elif data == "submenu_infoscommande":
        # On préfère ÉDITER pour éviter d’empiler des messages (1 seul message visuel vit)
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
        try:
            bot.edit_message_caption(
                caption=texte_infos,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=infoscommande_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            # Si l'édition échoue (message ancien, etc.), on remplace proprement
            send_clean_photo(
                chat_id,
                config.IMAGE_ACCUEIL_URL,
                caption=texte_infos,
                parse_mode='HTML',
                reply_markup=infoscommande_keyboard()
            )

    elif data == "submenu_contacts":
        texte_contacts = "<b><u>☎️ Contacts ☎️</u></b>\n\nPour toutes questions ou assistance, contactez-nous via WhatsApp :"
        try:
            bot.edit_message_caption(
                caption=texte_contacts,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=contacts_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            send_clean_photo(
                chat_id,
                config.IMAGE_ACCUEIL_URL,
                caption=texte_contacts,
                parse_mode='HTML',
                reply_markup=contacts_keyboard()
            )

    elif data == "submenu_liens":
        texte_liens = "<b><u>🌐 Liens Utiles 🌐</u></b>\n\nRetrouvez nos liens importants ci-dessous :"
        try:
            bot.edit_message_caption(
                caption=texte_liens,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=liens_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            send_clean_photo(
                chat_id,
                config.IMAGE_ACCUEIL_URL,
                caption=texte_liens,
                parse_mode='HTML',
                reply_markup=liens_keyboard()
            )

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
