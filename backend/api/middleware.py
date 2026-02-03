"""
Middleware pour authentification et autorisations
"""

import base64
import hmac
from werkzeug.security import check_password_hash
from flask import request, current_app
from functools import wraps
import logging
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

logger = logging.getLogger(__name__)

def _load_token(token):
    secret = current_app.config.get('SECRET_KEY')
    s = URLSafeTimedSerializer(secret)
    try:
        payload = s.loads(token, max_age=60 * 60 * 24 * 7)
        return payload
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def _basic_auth_payload():
    if not current_app.config.get('BASIC_AUTH_ENABLED', False):
        return None

    auth = request.headers.get('Authorization') or ''
    if not auth.startswith('Basic '):
        return None

    mode = (current_app.config.get('BASIC_AUTH_MODE') or 'static').lower()
    expected_user = (current_app.config.get('BASIC_AUTH_USERNAME') or '').strip()
    expected_pass = (current_app.config.get('BASIC_AUTH_PASSWORD') or '').strip()

    try:
        raw = base64.b64decode(auth.split(' ', 1)[1].strip()).decode('utf-8')
        user, pw = raw.split(':', 1)
    except Exception:
        return None

    if mode == 'db':
        try:
            from database.models import Utilisateur
            u = Utilisateur.query.filter_by(email=user, actif=True).first()
            if not u or not check_password_hash(u.mot_de_passe_hash or '', pw):
                return None
            return {
                'email': u.email,
                'role': 'admin',
                'auth': 'basic',
            }
        except Exception:
            return None

    if not (hmac.compare_digest(user, expected_user) and hmac.compare_digest(pw, expected_pass)):
        return None

    return {
        'email': expected_user,
        'role': 'admin',
        'auth': 'basic',
    }

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            payload = _load_token(token)
            if not payload:
                return {'erreur': 'Token invalide ou expiré'}, 401
        else:
            payload = _basic_auth_payload()
            if not payload:
                return {'erreur': 'Token manquant ou invalide'}, 401
        request.user_email = payload.get('email')
        request.user_role = payload.get('role')
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        payload = None
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            payload = _load_token(token)
        else:
            payload = _basic_auth_payload()

        if not payload:
            logger.warning(f"ADMIN_DENY unauthenticated {request.method} {request.path}")
            return {'erreur': 'Non authentifié'}, 401
        if payload.get('role') != 'admin':
            logger.warning(f"ADMIN_DENY forbidden {request.method} {request.path}")
            return {'erreur': 'Accès admin requis'}, 403
        request.user_email = payload.get('email')
        request.user_role = payload.get('role')
        logger.info(f"ADMIN_OK {request.user_email} {request.method} {request.path}")
        return f(*args, **kwargs)
    return decorated_function

def log_request(f):
    """
    Décorateur pour enregistrer les requêtes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"{request.method} {request.path}")
        return f(*args, **kwargs)
    
    return decorated_function
