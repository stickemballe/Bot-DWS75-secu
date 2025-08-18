import time
import requests
import json
from datetime import datetime, timedelta
import config

VERIFICATION_FILE = "user_verification.json"
VERIFICATION_EXPIRY_DAYS = 7

def load_verified_users():
    try:
        with open(VERIFICATION_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_verified_users(data):
    with open(VERIFICATION_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_user_verification(user_id: int):
    verified_users = load_verified_users()
    verified_users[str(user_id)] = datetime.utcnow().isoformat()
    save_verified_users(verified_users)
    config.logger.info(f"Vérification enregistrée pour l'utilisateur {user_id}")

def is_verification_valid(user_id: int):
    verified_users = load_verified_users()
    user_id_str = str(user_id)
    if user_id_str not in verified_users:
        return False
    try:
        last_verification_date = datetime.fromisoformat(verified_users[user_id_str])
        if datetime.utcnow() - last_verification_date > timedelta(days=VERIFICATION_EXPIRY_DAYS):
            return False
        return True
    except (ValueError, TypeError):
        return False

def verify_turnstile(token: str) -> bool:
    if not token:
        return False
    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={'secret': config.CAPTCHA_SECRET_KEY, 'response': token},
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("success", False)
    except requests.RequestException as e:
        config.logger.error(f"Erreur réseau Turnstile: {e}")
        return False

# --- FONCTION ANTI-FLOOD AJOUTÉE ---
user_requests = {} 
def is_flooding(user_id: int, limit: int = 3, period: int = 2) -> bool:
    """
    Vérifie si un utilisateur envoie trop de requêtes.
    Retourne True s'il dépasse la limite (par défaut, 3 requêtes en 2 secondes).
    """
    now = time.time()
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < period]
    
    if len(user_requests[user_id]) >= limit:
        config.logger.warning(f"Flood détecté pour l'utilisateur {user_id}")
        return True

    user_requests[user_id].append(now)
    return False
