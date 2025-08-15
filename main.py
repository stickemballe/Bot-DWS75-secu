import os
from flask import Flask
from threading import Thread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from security import check_security, validate_captcha, generate_captcha, captcha_pending

# === Config Railway ===
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)

# === Serveur pour UptimeRobot ===
app = Flask('')

@app.route('/')
def home():
    return "Bot actif avec sécurité"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# === Constantes ===
IMAGE_ACCUEIL_URL = 'https://file.garden/aIhdnTgFPho75N46/image-acceuil-bot-tlgrm.jpg'
MINIAPP_URL = 'https://dws75shop.com'
WHATSAPP_LINK = 'https://wa.me/33777824705'

user_last_message = {}

# === Menus ===
def menu_principal_keyboard(uid):
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("💫🛍 Menu Interactif 2.0 🛍💫", web_app=WebAppInfo(url=MINIAPP_URL)),
        InlineKeyboardButton("ℹ️ Infos & Commande 📲", callback_data="submenu_infoscommande"),
        InlineKeyboardButton("🛒 Commander 🛒", url=WHATSAPP_LINK),
        InlineKeyboardButton("☎️ Contacts ☎️", callback_data="submenu_contacts"),
        InlineKeyboardButton("🌐 Liens 🌐", callback_data="submenu_liens"),
    ]
    for btn in buttons[:3]:
        kb.add(btn)
    kb.add(buttons[3])
    kb.add(buttons[4])
    if uid == ADMIN_ID:
        kb.add(InlineKeyboardButton("⚙️ Paramètres (ADMIN) ⚙️", callback_data="submenu_parametres"))
    return kb

def infoscommande_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 Commander 🛒", url=WHATSAPP_LINK))
    kb.row(InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
           InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal"))
    return kb

def contacts_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("☎️ WhatsApp Standard ☎️", url="https://wa.me/33777824705"),
           InlineKeyboardButton("🆘 S.A.V  🆘", url="https://wa.me/33620832623"))
    kb.row(InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
           InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal"))
    return kb

def liens_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📲 Canal Telegram Secours 📲", url="https://t.me/+jh3S21ricEY5N2U8"),
        InlineKeyboardButton("🥔 Potato 🥔", url="https://dlptm.org/DWS75"),
        InlineKeyboardButton("☎️ WhatsApp Standard ☎️", url="https://wa.me/33777824705"),
        InlineKeyboardButton("📸 Instagram 📸", url="https://www.instagram.com/dryweedshop"),
        InlineKeyboardButton("👻 Snapchat 👻", url="https://snapchat.com/t/3ZCdfgNA")
    )
    kb.row(InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
           InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal"))
    return kb

# === Accueil ===
def send_welcome(message):
    chat_id = message.chat.id
    uid = message.from_user.id
    if chat_id in user_last_message:
        try:
            bot.delete_message(chat_id, user_last_message[chat_id])
        except:
            pass
    bot.send_photo(chat_id, IMAGE_ACCUEIL_URL)
    texte_accueil = (
        "<b><u>🤖 Bienvenue sur notre Bot 2.0 🤖</u></b>\n\n"
        "<b><u>💫 DWS75 - Depuis 2019 💫</u></b>\n\n"
        "Cliquez sur les boutons ci-dessous pour accéder à notre <b><u>menu interactif</u></b>, nous contacter ou trouver les infos utiles : 👇"
    )
    msg = bot.send_message(chat_id, texte_accueil, parse_mode='HTML', reply_markup=menu_principal_keyboard(uid))
    user_last_message[chat_id] = msg.message_id

# === Commandes ===
@bot.message_handler(commands=['start', 'menu', 'restart'])
def command_handler(message):
    uid = message.from_user.id
    if uid not in captcha_pending:
        question = generate_captcha(uid)
        bot.send_message(uid, f"🔐 Veuillez résoudre ce captcha pour continuer : {question}")
        return
    if not check_security(bot, message):
        return
    send_welcome(message)

# === Gestion messages texte ===
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    uid = message.from_user.id
    if uid in captcha_pending:
        if validate_captcha(bot, message):
            send_welcome(message)
        return
    if not check_security(bot, message):
        return

# === Callbacks ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not check_security(bot, call.message):
        return
    chat_id = call.message.chat.id
    data = call.data
    if chat_id in user_last_message:
        try:
            bot.delete_message(chat_id, user_last_message[chat_id])
        except:
            pass
    bot.answer_callback_query(call.id)
    if data == "menu_principal":
        send_welcome(call.message)
    elif data == "submenu_infoscommande":
        msg = bot.send_message(chat_id, "📦 Infos commandes...", parse_mode='HTML', reply_markup=infoscommande_keyboard())
        user_last_message[chat_id] = msg.message_id
    elif data == "submenu_contacts":
        msg = bot.send_message(chat_id, "☎️ Contacts...", parse_mode='HTML', reply_markup=contacts_keyboard())
        user_last_message[chat_id] = msg.message_id
    elif data == "submenu_liens":
        msg = bot.send_message(chat_id, "🌐 Liens utiles...", parse_mode='HTML', reply_markup=liens_keyboard())
        user_last_message[chat_id] = msg.message_id
    else:
        bot.answer_callback_query(call.id, "Fonction en cours de dev", show_alert=True)

# === Lancement ===
keep_alive()
print("Bot en ligne avec sécurité...")
bot.infinity_polling(skip_pending=True)

