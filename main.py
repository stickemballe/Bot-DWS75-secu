# bot_main_secure.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
import time

# --- STOCKAGE UTILISATEURS ---
user_data = {}  # {user_id: {"captcha": True/False, "blacklist": True/False, "last_msg": timestamp, "spam_count": int, "captcha_answer": str}}

# --- PARAMÈTRES ---
SPAM_LIMIT_SECONDS = 3
SPAM_MAX_COUNT = 5

# --- CAPTCHA SIMPLE ---
def generate_captcha():
    a, b = random.randint(1, 10), random.randint(1, 10)
    return f"{a} + {b}", str(a+b)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        question, answer = generate_captcha()
        user_data[user_id] = {"captcha": False, "blacklist": False, "last_msg": 0, "spam_count": 0, "captcha_answer": answer}
        await update.message.reply_text(f"Bienvenue ! Pour commencer, résolvez ce captcha : {question}")
        await send_main_buttons(update, context)
    else:
        if not user_data[user_id]["captcha"]:
            question, answer = generate_captcha()
            user_data[user_id]["captcha_answer"] = answer
            await update.message.reply_text(f"Captcha à résoudre : {question}")
        else:
            await update.message.reply_text("Vous avez déjà validé le captcha. Utilisez vos commandes ou boutons.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text

    # --- BLACKLIST ---
    if user_data.get(user_id, {}).get("blacklist", False):
        return

    # --- ANTI-SPAM ---
    now = time.time()
    last = user_data.get(user_id, {}).get("last_msg", 0)
    if now - last < SPAM_LIMIT_SECONDS:
        user_data[user_id]["spam_count"] += 1
        if user_data[user_id]["spam_count"] >= SPAM_MAX_COUNT:
            user_data[user_id]["blacklist"] = True
            await update.message.reply_text("Vous avez été blacklisté pour spam.")
        return
    else:
        user_data[user_id]["spam_count"] = 0
    user_data[user_id]["last_msg"] = now

    # --- CAPTCHA ---
    if not user_data[user_id]["captcha"]:
        if msg.strip() == user_data[user_id]["captcha_answer"]:
            user_data[user_id]["captcha"] = True
            await update.message.reply_text("Captcha validé ! Vous pouvez maintenant utiliser le bot.")
            await send_main_buttons(update, context)
        else:
            await update.message.reply_text("Captcha incorrect. Essayez encore.")
        return

    # --- LOGIQUE DU BOT (MAIN) ---
    await update.message.reply_text(f"Commande reçue : {msg}")  # Ici tu peux remplacer par ton vrai traitement

# --- BOUTONS INLINE ---
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # Vérification captcha + blacklist
    if user_data.get(user_id, {}).get("blacklist", False):
        await query.edit_message_text("Vous êtes blacklisté et ne pouvez pas utiliser ce bouton.")
        return
    if not user_data.get(user_id, {}).get("captcha", False):
        await query.edit_message_text("Vous devez d'abord valider le captcha.")
        return

    # --- LOGIQUE BOT POUR LES BOUTONS ---
    await query.edit_message_text(f"Vous avez cliqué sur : {query.data}")

async def send_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Exemple de boutons principaux du bot
    keyboard = [
        [InlineKeyboardButton("Bouton 1", callback_data="btn1"),
         InlineKeyboardButton("Bouton 2", callback_data="btn2")],
        [InlineKeyboardButton("Bouton 3", callback_data="btn3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choisissez une option :", reply_markup=reply_markup)

# --- SETUP BOT ---
BOT_TOKEN = "TON_BOT_TOKEN_ICI"
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
