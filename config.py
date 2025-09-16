import os
import logging
from dotenv import load_dotenv

# --- Chargement .env ---
load_dotenv()

# --- Logging de base ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Secrets et configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CAPTCHA_SECRET_KEY = os.getenv("CAPTCHA_SECRET_KEY")

# Compat : accepte ADMIN_IDS="id1,id2" OU ADMIN_ID="id_unique"
_raw_admins = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "")).replace(" ", "")
ADMIN_IDS = [int(x) for x in _raw_admins.split(",") if x]

# ✅ Compat descendante : expose aussi ADMIN_ID si l'ancien code l'utilise
ADMIN_ID = int(os.getenv("ADMIN_ID", str(ADMIN_IDS[0]) if ADMIN_IDS else "0"))

# URLs de ton projet
MINIAPP_URL = 'https://www.dws75shop.com/'
BOT_VERIFY_URL = 'https://www.dws75shop.com/bot-verify'
IMAGE_ACCUEIL_URL = 'https://file.garden/aIhdnTgFPho75N46/image-acceuil-bot-tlgrm.jpg'
WHATSAPP_LINK = 'https://wa.me/33777824705'
WHATSAPP_SAV_LINK = 'https://wa.me/33620832623'
TELEGRAM_SECOURS_URL = 'https://t.me/+jh3S21ricEY5N2U8'
POTATO_URL = 'https://dlptm.org/DWS75'
INSTAGRAM_URL = 'https://www.instagram.com/dryweedshopsigsh=aTR3b3lyb2Y3ZjJo&utm_source=qr'
SNAPCHAT_URL = 'https://snapchat.com/t/3ZCdfgNA'

# --- Validations minimales ---
if not BOT_TOKEN or not CAPTCHA_SECRET_KEY:
    raise ValueError("Les secrets du bot ou du captcha sont manquants dans .env")

if not ADMIN_IDS:
    logger.warning("Aucun admin défini. Renseigne ADMIN_IDS ou ADMIN_ID dans les variables d'environnement.")

# --- Helper pratique ---
def is_admin(user_id: int) -> bool:
    """Retourne True si l'utilisateur est admin (défini dans ADMIN_IDS)."""
    return user_id in ADMIN_IDS
