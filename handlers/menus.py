from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import config

def menu_principal_keyboard(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton("💫🛍 Menu Interactif 2.0 🛍💫", web_app=WebAppInfo(url=config.MINIAPP_URL)),
        InlineKeyboardButton("ℹ️ Infos & Commande 📲", callback_data="submenu_infoscommande"),
        InlineKeyboardButton("🛒 Commander 🛒", url=config.WHATSAPP_LINK),
        InlineKeyboardButton("☎️ Contacts ☎️", callback_data="submenu_contacts"),
        InlineKeyboardButton("🌐 Liens 🌐", callback_data="submenu_liens"),
    ]
    kb.add(*buttons)
    if uid == config.ADMIN_ID:
        kb.add(InlineKeyboardButton("⚙️ Paramètres (ADMIN) ⚙️", callback_data="submenu_parametres"))
    return kb

def infoscommande_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 Commander 🛒", url=config.WHATSAPP_LINK))
    kb.row(
        InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
        InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")
    )
    return kb

def contacts_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("☎️ WhatsApp Standard ☎️", url=config.WHATSAPP_LINK),
        InlineKeyboardButton("🆘 S.A.V  🆘", url=config.WHATSAPP_SAV_LINK)
    )
    kb.row(
        InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
        InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")
    )
    return kb

def liens_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📲 Canal Telegram Secours 📲", url=config.TELEGRAM_SECOURS_URL),
        InlineKeyboardButton("🥔 Potato 🥔", url=config.POTATO_URL),
        InlineKeyboardButton("☎️ WhatsApp Standard ☎️", url=config.WHATSAPP_LINK),
        InlineKeyboardButton("📸 Instagram 📸", url=config.INSTAGRAM_URL),
        InlineKeyboardButton("👻 Snapchat 👻", url=config.SNAPCHAT_URL)
    )
    kb.row(
        InlineKeyboardButton("◀️ Retour", callback_data="menu_principal"),
        InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_principal")
    )
    return kb

def verification_keyboard() -> InlineKeyboardMarkup:
    """
    Crée un clavier qui ouvre la page de vérification comme une MINI APP.
    """
    kb = InlineKeyboardMarkup(row_width=1)
    button = InlineKeyboardButton(
        text="✅ Me Vérifier Maintenant",
        web_app=WebAppInfo(url=config.BOT_VERIFY_URL)
    )
    kb.add(button)
    return kb