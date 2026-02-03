"""
Routes pour servir l'interface web (frontend)
À ajouter à app.py comme blueprint supplémentaire
"""

from flask import Blueprint, render_template, send_from_directory, current_app, redirect
import os

# Chemins absolus vers le dossier frontend pour éviter les chemins relatifs cassés
frontend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
static_folder = os.path.join(frontend_root, 'static')
template_folder = os.path.join(frontend_root, 'templates')

frontend_bp = Blueprint('frontend', __name__, 
                       static_folder=static_folder,
                       template_folder=template_folder)


@frontend_bp.app_context_processor
def inject_branding():
    return {
        'BRAND_NAME': current_app.config.get('BRAND_NAME', "Stat'Innov Developpement"),
        'BRAND_SHORT_NAME': current_app.config.get('BRAND_SHORT_NAME', 'SinDev'),
        'BRAND_WEBSITE': current_app.config.get('BRAND_WEBSITE', 'https://sindevstat.com'),
        'BRAND_LOGO_URL': current_app.config.get('BRAND_LOGO_URL', '/static/img/sindev-logo.jpeg'),
        'CONTACT_EMAIL': current_app.config.get('CONTACT_EMAIL', ''),
        'CONTACT_PHONE': current_app.config.get('CONTACT_PHONE', ''),
        'CONTACT_ADDRESS': current_app.config.get('CONTACT_ADDRESS', ''),
    }

@frontend_bp.route('/')
def accueil():
    """Page d'accueil"""
    return render_template('index.html')

@frontend_bp.route('/offres')
def offres():
    """Page de liste des offres"""
    return render_template('offres.html')

@frontend_bp.route('/offres/<int:offre_id>')
def detail_offre(offre_id):
    """Page détail d'une offre"""
    return render_template('offre-detail.html', offre_id=offre_id)

@frontend_bp.route('/mots-cles')
def mots_cles():
    """Page de gestion des mots-clés (admin)"""
    return render_template('mots-cles.html')

@frontend_bp.route('/scheduler')
def scheduler_dashboard():
    """Dashboard du scheduler (admin)"""
    return render_template('scheduler.html')

@frontend_bp.route('/connexion')
def connexion():
    """Page de connexion"""
    if current_app.config.get('BASIC_AUTH_ENABLED', False):
        return redirect('/')
    return render_template('connexion.html')


@frontend_bp.route('/admin/compte')
def admin_compte():
    """Page admin pour modifier les identifiants"""
    return render_template('admin-compte.html')

# Route de debug pour lister les templates disponibles (ne pas exposer en production)
@frontend_bp.route('/__debug/templates')
def debug_templates():
    from flask import current_app
    env = current_app.config.get('ENV') or os.getenv('FLASK_ENV', 'development')
    if (env or '').lower() == 'production':
        return {'erreur': 'Ressource non trouvée'}, 404
    env = current_app.jinja_env
    templates = list(env.list_templates())
    return {'templates': templates}

# Les fichiers statiques sont servis automatiquement par le blueprint via `static_folder`
# (route '/static/<path:filename>' fournie par Flask/Blueprint)
