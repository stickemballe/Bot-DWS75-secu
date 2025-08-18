import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CAPTCHA_SECRET_KEY = os.getenv("CAPTCHA_SECRET_KEY")

if not BOT_TOKEN or not CAPTCHA_SECRET_KEY:
    raise ValueError("Les secrets du bot ou du captcha sont manquants dans .env")

# L'URL de la boutique principale (la Mini App)
MINIAPP_URL = 'https://www.dws75shop.com/'
# L'URL de la page de vérification qui s'ouvrira en Mini App
BOT_VERIFY_URL = 'https://www.dws75shop.com/bot-verify' # Changez si votre URL est différente

IMAGE_ACCUEIL_URL = 'https://file.garden/aIhdnTgFPho75N46/image-acceuil-bot-tlgrm.jpg'
WHATSAPP_LINK = 'https://wa.me/33777824705'
WHATSAPP_SAV_LINK = 'https://wa.me/33620832623'
TELEGRAM_SECOURS_URL = 'https://t.me/+jh3S21ricEY5N2U8'
POTATO_URL = 'https://dlptm.org/DWS75'
INSTAGRAM_URL = 'https://www.instagram.com/dryweedshopsigsh=aTR3b3lyb2Y3ZjJo&utm_source=qr'
SNAPCHAT_URL = 'https://snapchat.com/t/3ZCdfgNA'