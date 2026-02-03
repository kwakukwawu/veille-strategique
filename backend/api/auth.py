"""
Authentification et gestion des utilisateurs
"""

from flask import Blueprint, request, current_app
from flask import Response
from functools import wraps
import logging
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta

from database.models import Utilisateur, db
from api.middleware import require_admin

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/reauth', methods=['GET'])
def reauth():
    realm = (current_app.config.get('BASIC_AUTH_REALM') or 'Protected')
    return Response('Ré-authentification requise', 401, {
        'WWW-Authenticate': f'Basic realm="{realm}"'
    })
logger = logging.getLogger(__name__)

_LOGIN_ATTEMPTS = {}


def _client_ip():
    # Best-effort: if behind a proxy, X-Forwarded-For may exist.
    xff = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    return xff or (request.remote_addr or 'unknown')


def _rate_limit_login():
    max_attempts = int(current_app.config.get('LOGIN_RATE_LIMIT_MAX', 10))
    window_seconds = int(current_app.config.get('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 600))
    ip = _client_ip()
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    attempts = _LOGIN_ATTEMPTS.get(ip, [])
    attempts = [t for t in attempts if t >= window_start]
    _LOGIN_ATTEMPTS[ip] = attempts

    if len(attempts) >= max_attempts:
        return False

    attempts.append(now)
    _LOGIN_ATTEMPTS[ip] = attempts
    return True

def _get_serializer():
    secret = current_app.config.get('SECRET_KEY')
    return URLSafeTimedSerializer(secret)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Connexion: vérifie email/mot de passe et retourne un token signé"""
    if not _rate_limit_login():
        return {'erreur': 'Trop de tentatives, réessayez plus tard'}, 429

    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return {'erreur': 'Email et mot de passe requis'}, 400

    email = data['email']
    password = data['password']

    user = Utilisateur.query.filter_by(email=email, actif=True).first()
    if not user or not check_password_hash(user.mot_de_passe_hash or '', password):
        logger.warning(f"Tentative de connexion échouée pour {email}")
        return {'erreur': 'Identifiants invalides'}, 401

    s = _get_serializer()
    token = s.dumps({'email': email, 'role': user.role})

    logger.info(f"Connexion réussie pour {email}")
    return {
        'token': token,
        'email': email,
        'role': user.role,
        'message': 'Connexion réussie'
    }, 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    logger.info('Déconnexion')
    return {'message': 'Déconnexion réussie'}, 200

@auth_bp.route('/profil', methods=['GET'])
def profil():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Basic '):
        import base64
        import hmac

        mode = (current_app.config.get('BASIC_AUTH_MODE') or 'static').lower()
        expected_user = (current_app.config.get('BASIC_AUTH_USERNAME') or '').strip()
        expected_pass = (current_app.config.get('BASIC_AUTH_PASSWORD') or '').strip()

        try:
            raw = base64.b64decode(auth_header.split(' ', 1)[1].strip()).decode('utf-8')
            user, pw = raw.split(':', 1)
        except Exception:
            return {'erreur': 'Identifiants invalides'}, 401

        if mode == 'db':
            u = Utilisateur.query.filter_by(email=user, actif=True).first()
            if not u or not check_password_hash(u.mot_de_passe_hash or '', pw):
                return {'erreur': 'Identifiants invalides'}, 401
            return {
                'email': u.email,
                'role': 'admin'
            }, 200

        if not (hmac.compare_digest(user, expected_user) and hmac.compare_digest(pw, expected_pass)):
            return {'erreur': 'Identifiants invalides'}, 401
        return {
            'email': expected_user,
            'role': 'admin'
        }, 200

    token = auth_header.replace('Bearer ', '')
    if not token:
        return {'erreur': 'Token manquant'}, 401

    s = _get_serializer()
    try:
        payload = s.loads(token, max_age=60 * 60 * 24 * 7)  # 7 jours
    except SignatureExpired:
        return {'erreur': 'Token expiré'}, 401
    except BadSignature:
        return {'erreur': 'Token invalide'}, 401

    return {
        'email': payload.get('email'),
        'role': payload.get('role')
    }, 200


@auth_bp.route('/change-credentials', methods=['POST'])
@require_admin
def change_credentials():
    """Modifier les identifiants admin (email/mot de passe) après vérification de l'ancien mot de passe."""
    data = request.get_json(silent=True) or {}
    current_password = (data.get('current_password') or '').strip()
    new_email = (data.get('new_email') or '').strip()
    new_password = (data.get('new_password') or '').strip()

    if not current_password:
        return {'erreur': 'Mot de passe actuel requis'}, 400
    if not new_email and not new_password:
        return {'erreur': 'Aucune modification demandée'}, 400

    # L'email courant est déterminé par le middleware (Bearer token ou Basic Auth)
    email = getattr(request, 'user_email', None)
    if not email:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {'erreur': 'Token invalide ou expiré'}, 401
        s = _get_serializer()
        try:
            payload = s.loads(token, max_age=60 * 60 * 24 * 7)
            email = payload.get('email')
        except Exception:
            return {'erreur': 'Token invalide ou expiré'}, 401
    user = Utilisateur.query.filter_by(email=email, actif=True).first()
    if not user:
        # En mode Basic Auth "static", l'admin peut ne pas exister dans la table.
        # On le crée à la volée pour permettre la gestion d'identifiants via l'UI.
        mode = (current_app.config.get('BASIC_AUTH_MODE') or 'static').lower()
        if mode == 'static':
            try:
                expected_pass = (current_app.config.get('BASIC_AUTH_PASSWORD') or '').strip()
                user = Utilisateur(
                    email=email,
                    nom_complet='Administrateur',
                    mot_de_passe_hash=generate_password_hash(expected_pass),
                    role='admin',
                    actif=True,
                )
                db.session.add(user)
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return {'erreur': 'Utilisateur introuvable'}, 404
        else:
            return {'erreur': 'Utilisateur introuvable'}, 404

    if not check_password_hash(user.mot_de_passe_hash or '', current_password):
        return {'erreur': 'Mot de passe actuel incorrect'}, 401

    if new_email:
        exists = Utilisateur.query.filter(Utilisateur.email == new_email, Utilisateur.id != user.id).first()
        if exists:
            return {'erreur': 'Email déjà utilisé'}, 409
        user.email = new_email

    if new_password:
        if len(new_password) < 6:
            return {'erreur': 'Mot de passe trop court (min 6 caractères)'}, 400
        user.mot_de_passe_hash = generate_password_hash(new_password)

    user.derniere_connexion = None
    try:
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return {'erreur': 'Erreur lors de la mise à jour'}, 500

    # Nouveau token (si email changé)
    s = _get_serializer()
    new_token = s.dumps({'email': user.email, 'role': user.role})
    return {
        'message': 'Identifiants mis à jour',
        'token': new_token,
        'email': user.email,
        'role': user.role,
    }, 200
