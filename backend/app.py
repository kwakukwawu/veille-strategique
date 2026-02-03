"""
Application Flask principale
Point d'entrée pour Veille Stratégique
"""

import os
import sys
import logging
import base64
import hmac
from werkzeug.security import check_password_hash
from flask import Flask, request, Response
from flask_cors import CORS

# Guard for Python versions incompatible with installed SQLAlchemy
if sys.version_info >= (3, 12):
    # Avoid importing SQLAlchemy which may raise obscure errors under newer Python
    if not (os.getenv('RENDER') or os.getenv('RENDER_SERVICE_ID') or os.getenv('RENDER_EXTERNAL_URL')):
        raise SystemExit('Python >= 3.12 détecté — utilisez Python 3.11 pour exécuter Veille Stratégique. Voir backend/setup-python311.ps1 pour automatiser l\'installation.')

# Configuration
from config import get_config

# Base de données
from database.database import init_db
from database.models import db

# Scheduler
from scraping.scheduler import scheduler

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config=None):
    """
    Factory pour créer et configurer l'application Flask
    
    Args:
        config: Objet de configuration (optionnel)
    """
    # Désactiver le dossier static par défaut pour éviter de masquer notre /static personnalisé
    app = Flask(__name__, static_folder=None)
    
    # Charger la configuration
    if config is None:
        config = get_config()
    app.config.from_object(config)
    
    # Initialiser les extensions
    db.init_app(app)

    # CORS: limiter aux routes API uniquement (l'UI est servie en same-origin).
    try:
        allowed = app.config.get('CORS_ORIGINS')
    except Exception:
        allowed = None
    if not allowed:
        allowed = [
            'http://127.0.0.1:5000',
            'http://localhost:5000',
        ]
    CORS(app, resources={r"/api/*": {"origins": allowed}})
    scheduler.init_app(app)

    # Protection HTTP Basic (mot de passe requis avant toute page)
    @app.before_request
    def basic_auth_gate():
        if not app.config.get('BASIC_AUTH_ENABLED', False):
            return None

        path = request.path or ''
        for p in (app.config.get('BASIC_AUTH_EXEMPT_PATH_PREFIXES') or []):
            if path.startswith(p):
                return None

        mode = (app.config.get('BASIC_AUTH_MODE') or 'static').lower()
        expected_user = (app.config.get('BASIC_AUTH_USERNAME') or '').strip()
        expected_pass = (app.config.get('BASIC_AUTH_PASSWORD') or '').strip()
        realm = (app.config.get('BASIC_AUTH_REALM') or 'Protected')

        auth = request.headers.get('Authorization') or ''
        if not auth.startswith('Basic '):
            return Response('Authentification requise', 401, {
                'WWW-Authenticate': f'Basic realm="{realm}"'
            })

        try:
            raw = base64.b64decode(auth.split(' ', 1)[1].strip()).decode('utf-8')
            user, pw = raw.split(':', 1)
        except Exception:
            return Response('Authentification invalide', 401, {
                'WWW-Authenticate': f'Basic realm="{realm}"'
            })

        if mode == 'db':
            try:
                from database.models import Utilisateur
                u = Utilisateur.query.filter_by(email=user, actif=True).first()
                if not u or not check_password_hash(u.mot_de_passe_hash or '', pw):
                    raise ValueError('invalid')
            except Exception:
                return Response('Accès refusé', 401, {
                    'WWW-Authenticate': f'Basic realm="{realm}"'
                })
            return None

        ok_user = hmac.compare_digest(user, expected_user)
        ok_pass = hmac.compare_digest(pw, expected_pass)
        if not (ok_user and ok_pass):
            return Response('Accès refusé', 401, {
                'WWW-Authenticate': f'Basic realm="{realm}"'
            })
        return None

    # Headers de sécurité (compatibles avec les scripts inline actuels)
    @app.after_request
    def add_security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        # CSP: on garde 'unsafe-inline' car les templates ont des <script> inline.
        # À durcir plus tard en passant à des nonces.
        resp.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
        )
        if app.config.get('ENV') == 'production' or os.getenv('FLASK_ENV') == 'production':
            resp.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return resp
    
    # Initialiser la base de données
    with app.app_context():
        init_db(app)
    
    # Enregistrer les blueprints (routes)
    from api.routes import api_bp
    from api.auth import auth_bp
    from api.frontend_routes import frontend_bp
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(frontend_bp, url_prefix='')
    
    # Route de santé (health check)
    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'healthy', 'service': 'veille-strategique'}, 200
    
    # Infos API (évite le conflit avec la page d'accueil servie par le frontend)
    @app.route('/api-info', methods=['GET'])
    def api_info():
        return {
            'nom': 'Veille Stratégique API',
            'version': '1.0.0',
            'description': 'Plateforme de collecte et monitoring d\'offres d\'appels',
            'endpoints': {
                'offres': '/api/offres',
                'mots_cles': '/api/mots-cles',
                'sources': '/api/sources',
                'scheduler': '/api/scheduler',
                'sante': '/health'
            }
        }, 200
    
    # Gestionnaire d'erreurs
    @app.errorhandler(404)
    def not_found(error):
        return {'erreur': 'Ressource non trouvée'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Erreur serveur: {str(error)}", exc_info=True)
        return {'erreur': 'Erreur serveur interne'}, 500

    # Démarrer le scheduler automatiquement au démarrage de l'app.
    # Avec use_reloader=False (choix actuel), il n'y a pas de double process.
    # On peut donc démarrer le scheduler en développement aussi.
    try:
        if not scheduler.scheduler.running:
            scheduler.demarrer()
    except Exception as e:
        logger.error(f"Erreur démarrage scheduler: {str(e)}", exc_info=True)
    
    logger.info("✓ Application Flask créée et configurée")
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Environnement
    env = os.getenv('FLASK_ENV', 'development')
    debug = env == 'development'
    port = int(os.getenv('PORT', '5000'))
    
    logger.info(f"Démarrage en mode: {env}")
    logger.info(f"Debug: {debug}")
    
    # Lancer l'application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False,
        threaded=True
    )
