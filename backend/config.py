"""
Configuration de la plateforme Veille Stratégique
Gère les paramètres d'environnement et la configuration globale
"""

import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    
    # Base de données
    _PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _DEFAULT_SQLITE_PATH = os.path.join(_PROJECT_ROOT, 'instance', 'veille_strategique.db')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{_DEFAULT_SQLITE_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': int(os.getenv('SQLITE_BUSY_TIMEOUT', 30))
        }
    }
    
    # Clés secrètes
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Scheduler (tâches planifiées)
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = os.getenv('SCHEDULER_TIMEZONE', 'Africa/Abidjan')
    
    # Scraping
    SCRAPING_TIMEOUT = int(os.getenv('SCRAPING_TIMEOUT', 30))  # secondes
    SCRAPING_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # API
    API_TITLE = 'Veille Stratégique API'
    API_VERSION = '1.0.0'

    # Sécurité
    LOGIN_RATE_LIMIT_MAX = int(os.getenv('LOGIN_RATE_LIMIT_MAX', 10))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 600))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    
    # Partenaires et sources
    PARTENAIRES = {
        'organisation': ['GIZ', 'ENABEL', 'FIRCA', 'ANADER', 'MINADER', 'PAM', 'FAO', 'UE', 'AFD', 'PNUD', 'Banque Mondiale', 'BAD'],
        'gouvernance': ['MINADER', 'ANADER', 'FIRCA']
    }
    
    # Couleurs du logo (orange, bleu, noir)
    THEME_COLORS = {
        'primary': '#FF8C00',      # Orange
        'secondary': '#0066CC',     # Bleu
        'dark': '#1a1a1a',         # Noir
        'light': '#f5f5f5'         # Gris clair
    }

    # Branding (Sindev)
    BRAND_NAME = os.getenv('BRAND_NAME', "Stat'Innov Developpement")
    BRAND_SHORT_NAME = os.getenv('BRAND_SHORT_NAME', 'SinDev')
    BRAND_WEBSITE = os.getenv('BRAND_WEBSITE', 'https://sindevstat.com')
    BRAND_LOGO_URL = os.getenv('BRAND_LOGO_URL', '/static/img/sindev-logo.jpeg')
    
    # Contact
    CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', 'sindevstat@sindevstat.com')
    CONTACT_PHONE = os.getenv('CONTACT_PHONE', '+225 07 07 38 72 55')
    CONTACT_ADDRESS = os.getenv('CONTACT_ADDRESS', 'Cocody Angré, cité groupement 4000D')

    TABLEAU_VEILLE_ACTEURS = [
        {'categorie': 'ONG', 'structure': 'CARE', 'lien': 'https://www.care.org'},
        {'categorie': 'ONG', 'structure': 'OXFAM', 'lien': 'https://www.oxfam.org'},
        {'categorie': 'ONG', 'structure': 'AVSF', 'lien': 'https://www.avsf.org'},
        {'categorie': 'ONG', 'structure': 'HELVETAS', 'lien': 'https://www.helvetas.org'},
        {'categorie': 'ONG', 'structure': 'SNV', 'lien': 'https://snv.org'},
        {'categorie': 'ONG', 'structure': 'AGRISUD', 'lien': 'https://www.agrisud.org'},
        {'categorie': 'ONG', 'structure': 'SOLIDARITÉS', 'lien': 'https://www.solidarites.org'},

        {'categorie': 'Média', 'structure': 'Fraternité Matin', 'lien': 'https://www.fratmat.info/'},

        {'categorie': 'Marchés publics', 'structure': 'Marchés Publics CI (DGMP)', 'lien': 'https://www.marchespublics.ci/appel_offre'},
        {'categorie': 'Marchés publics', 'structure': 'ARCOP', 'lien': 'https://arcop.ci/documentation/avis/avis-dappel-doffres/'},
        {'categorie': 'Infrastructures', 'structure': 'AGEROUTE CI', 'lien': 'https://ageroute.ci/appels-d-offres/avis-d-appel-d-offres-de-travaux'},
        {'categorie': 'Numérique / TIC', 'structure': 'ANSUT', 'lien': 'https://ansut.ci/recrutement/appel-a-prestataire/'},
        {'categorie': 'Infrastructures', 'structure': "Fonds d’Entretien Routier (FER)", 'lien': 'https://www.fer.ci/appels_offre/procedures'},

        {'categorie': "Structures techniques de l’État", 'structure': 'INS', 'lien': 'http://www.ins.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'OCPV', 'lien': 'https://www.ocpv.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'MINADER', 'lien': 'http://www.agriculture.gouv.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'ANADER', 'lien': 'https://www.anader.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'ONDR', 'lien': 'http://www.ondr.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'CIAPOL', 'lien': 'http://www.ciapol.ci'},
        {'categorie': "Structures techniques de l’État", 'structure': 'CNRA', 'lien': 'https://www.cnra.ci'},

        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'FENACOVICI', 'lien': 'http://www.fenascovici.com'},
        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'FIRCA', 'lien': 'http://www.firca.ci'},
        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'ANOPACI', 'lien': ''},
        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'APROMAC', 'lien': 'https://apromac.ci/'},
        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'Intercoton', 'lien': 'https://www.intercoton.ci/'},
        {'categorie': 'Faîtières agricoles / Organisations professionnelles', 'structure': 'CADES/COOP-CA', 'lien': 'https://www.cadesa-coop-ca.net/'},

        {'categorie': 'PTF', 'structure': 'BAD', 'lien': 'https://www.afdb.org'},
        {'categorie': 'PTF', 'structure': 'UE', 'lien': 'https://european-union.europa.eu'},
        {'categorie': 'PTF', 'structure': 'GIZ', 'lien': 'https://www.giz.de/en/html/index.html'},
        {'categorie': 'PTF', 'structure': 'AFD', 'lien': 'https://www.afd.fr'},
        {'categorie': 'PTF', 'structure': 'ENABEL', 'lien': 'https://www.enabel.be'},
        {'categorie': 'PTF', 'structure': 'JICA (JETRO)', 'lien': 'https://www.jica.go.jp'},
        {'categorie': 'PTF', 'structure': 'FAO', 'lien': 'https://www.fao.org'},
        {'categorie': 'PTF', 'structure': 'PAM', 'lien': 'https://www.wfp.org'},

        {'categorie': 'Collectivités territoriales', 'structure': 'Conseil régional', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Préfectures', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Sous-Préfectures', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Communes rurales', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Mairies', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Directions départementales', 'lien': ''},
        {'categorie': 'Collectivités territoriales', 'structure': 'Districts autonomes', 'lien': ''},

        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'Banques', 'lien': ''},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'IMF', 'lien': 'https://www.imf.org/fr/Countries/ResRep/CIV'},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'AgDEvCo', 'lien': 'https://www.agdevco.com'},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'OLAM', 'lien': 'https://www.olamgroup.com'},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'NESTLE CI', 'lien': 'https://www.nestle.ci'},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': 'SIFCA', 'lien': 'https://www.groupesifca.com'},
        {'categorie': "Entreprises/Fonds d’investissement", 'structure': "TONY’S Chocolonely", 'lien': 'https://tonyschocolonely.com'},
    ]

    STRUCTURES_SCRAPING_TARGETS = [
        {
            'structure': 'ANADER',
            'urls_a_scraper': [
                'https://www.anader.ci/appels-doffre/',
                'https://www.anader.ci/carriere/',
            ],
        },
        {
            'structure': 'FIRCA',
            'urls_a_scraper': [
                'https://firca.ci/offres/appels-doffres/',
                'https://firca.ci/offres/',
                'https://firca.ci/offres/resultats-des-appels-doffres/',
            ],
        },
        {
            'structure': 'BAD',
            'urls_a_scraper': [
                'https://www.afdb.org/en/about-us/corporate-procurement/procurement-notices/current-solicitations',
                'https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/request-for-expression-of-interest',
                'https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/invitation-for-bids',
            ],
        },
        {
            'structure': 'Banque Mondiale',
            'urls_a_scraper': [
                'https://projects.worldbank.org/en/projects-operations/procurement',
            ],
        },
        {
            'structure': 'UE (TED)',
            'urls_a_scraper': [
                'https://ted.europa.eu/en/',
                'https://ted.europa.eu/en/advanced-search',
            ],
        },
        {
            'structure': 'GIZ',
            'urls_a_scraper': [
                'https://www.giz.de/en/workingwithgiz/bidding_procurement.html',
                'https://www.giz.de/en/partner/contractor/tenders',
                'https://www.giz.de/en/worldwide/115442.html',
            ],
        },
        {
            'structure': 'AFD',
            'urls_a_scraper': [
                'https://www.afd.fr/en/bid-invitations-and-procurement',
                'https://www.afd.fr/en/suppliers',
            ],
        },
        {
            'structure': 'ENABEL',
            'urls_a_scraper': [
                'https://www.enabel.be/public-procurement/',
                'https://www.enabel.be/public-procurement/?in_category%5B%5D=all&in_country=1375&is_status=all',
            ],
        },
        {
            'structure': 'FAO',
            'urls_a_scraper': [
                'https://www.fao.org/unfao/procurement/bidding-opportunities/en/',
                'https://www.fao.org/unfao/procurement/en',
            ],
        },
        {
            'structure': 'PAM (WFP)',
            'urls_a_scraper': [
                'https://www.wfp.org/procurement',
                'https://www.wfp.org/do-business-with-wfp',
            ],
        },
        {
            'structure': 'PNUD (UNDP)',
            'urls_a_scraper': [
                'https://procurement-notices.undp.org/',
                'https://procurement-notices.undp.org/index.cfm?order_by=cty_sht_t',
            ],
        },

        {
            'structure': 'Marchés Publics CI (DGMP)',
            'urls_a_scraper': [
                'https://www.marchespublics.ci/appel_offre',
            ],
        },
        {
            'structure': 'ARCOP',
            'urls_a_scraper': [
                'https://arcop.ci/documentation/avis/avis-dappel-doffres/',
            ],
        },
        {
            'structure': 'AGEROUTE CI',
            'urls_a_scraper': [
                'https://ageroute.ci/appels-d-offres/avis-d-appel-d-offres-de-travaux',
                'https://ageroute.ci/appels-d-offres/avis-de-manifestation-d-interet/',
            ],
        },
        {
            'structure': 'ANSUT',
            'urls_a_scraper': [
                'https://ansut.ci/recrutement/appel-a-prestataire/',
                'https://ansut.ci/recrutement/',
            ],
        },
        {
            'structure': "Fonds d’Entretien Routier (FER)",
            'urls_a_scraper': [
                'https://www.fer.ci/appels_offre/procedures',
                'https://www.fer.ci/appels_offre/resultats_appels_offre/2',
            ],
        },
    ]

    _structures_targets_map = {t.get('structure'): t for t in STRUCTURES_SCRAPING_TARGETS if t.get('structure')}
    for _a in TABLEAU_VEILLE_ACTEURS:
        _structure = (_a or {}).get('structure')
        _lien = (_a or {}).get('lien')
        if not _structure or not _lien:
            continue
        if _structure in _structures_targets_map:
            continue
        _structures_targets_map[_structure] = {'structure': _structure, 'urls_a_scraper': [_lien]}
    STRUCTURES_SCRAPING_TARGETS = list(_structures_targets_map.values())

    # --- Attempt to merge automatically discovered targets (if present)
    try:
        import json
        discovered_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'scraping', 'discovered_targets.json')
        if os.path.exists(discovered_path):
            with open(discovered_path, 'r', encoding='utf-8') as fh:
                discovered = json.load(fh) or {}
            _dt_map = {t.get('structure'): t for t in STRUCTURES_SCRAPING_TARGETS if t.get('structure')}
            for _name, _urls in discovered.items():
                if not _urls:
                    continue
                # normalize list of urls
                _clean_urls = [u for u in (_urls or []) if u]
                if _name in _dt_map:
                    existing = _dt_map[_name].get('urls_a_scraper', []) or []
                    for _u in _clean_urls:
                        if _u not in existing:
                            existing.append(_u)
                    _dt_map[_name]['urls_a_scraper'] = existing
                else:
                    _dt_map[_name] = {'structure': _name, 'urls_a_scraper': _clean_urls}
            STRUCTURES_SCRAPING_TARGETS = list(_dt_map.values())
    except Exception:
        # If anything goes wrong do not break configuration loading
        pass

    SINDEV_FOCUS_ENABLED = True
    SINDEV_FOCUS_TERMS = [
        'étude', 'etude', 'études', 'etudes',
        'socio-économique', 'socio economique', 'socioeconomique',
        'enquête', 'enquete', 'survey',
        'étude de marché', 'etude de marche', 'market research',
        'gestion de projets', 'project management',
        'renforcement des capacités', 'renforcement des capacites', 'capacity building',
        'assistance technique', 'technical assistance',
        'statistique', 'statistics', 'data',
        'télédétection', 'teledetection', 'remote sensing',
        'imagerie satellitaire', 'satellite imagery',
        'collecte de données', 'collecte des données', 'data collection',
        'évaluation', 'evaluation', 'monitoring',

        'suivi-évaluation', 'suivi evaluation', 'monitoring and evaluation', 'm&e',
        'ligne de base', 'baseline',
        'tdr', 't.d.r', 'termes de référence', 'termes de reference',
        'consultant', 'consultance', 'consulting',
        'appel à candidatures', 'appel a candidatures', 'appel à candidature', 'appel a candidature',
        'avis de manifestation', 'manifestation d\'intérêt', 'manifestation d\'interet',
        'ami', 'aoi', 'dao',
        'audit', 'diagnostic',
        'étude d\'impact', 'etude d\'impact', 'impact assessment',
    ]

    # Optionnel: renforcer le focus Côte d'Ivoire (désactivé par défaut)
    SINDEV_CI_ONLY = True
    SINDEV_CI_TERMS = [
        'côte d\'ivoire',
        'cote d\'ivoire',
        'côte d ivoire',
        'cote d ivoire',
        'cote divoire',
        'cotedivoire',
        'ivory coast',
        'république de côte d\'ivoire',
        'republique de cote d\'ivoire',
        'civ',
    ]

    SINDEV_CI_GEO_TERMS = [
        'côte d\'ivoire', 'cote d\'ivoire', 'ivory coast',
        'yamoussoukro', 'bouaké', 'bouake', 'san pedro', 'san-pedro', 'korhogo',
        'daloa', 'man', 'gagnoa', 'abengourou', 'odienné', 'odienne', 'bondoukou',
        'dimbokro', 'agnoibilékrou', 'agnoibilekrou', 'agboville', 'grand-bassam', 'grand bassam',
        'bongouanou', 'daoukro', 'issia', 'sassandra', 'séguéla', 'seguela',
        'divo', 'dive', 'adiake', 'adzopé', 'adzopé', 'adzopé', 'adzopé',
        'adzope', 'aboisso', 'abobo', 'anyama', 'bingerville', 'cocody', 'yopougon',
        'treichville', 'marcory', 'plateau', 'port-bouët', 'port-bouet',
        'bassam', 'bingerville', 'abengourou', 'akéssé', 'akessé', 'akoupe', 'akoupe',
        'tiassalé', 'tiassale', 'sikensi', 'dabou',
        'soubré', 'soubre', 'méagui', 'meagui', 'buyo', 'guiglo', 'bangolo',
        'duekoue', 'duékoué', 'taï', 'tai',
        'bouaflé', 'bouafle', 'sinfra', 'zuénoula', 'zuenoula',
        'toumodi', 'touba', 'katiola', 'ferkessédougou', 'ferkessedougou',
        'boundiali', 'dabakala', 'bouna',
        'séguélon', 'seguelon', 'tingrela',
        'lakota', 'oumé', 'oume',
        'cavally', 'gbêkê', 'gbeke', 'woroba', 'savanes', 'lagunes',
        'district autonome d\'abidjan', 'district autonome de yamoussoukro',
        'bas-sassandra', 'bas sassandra',
        'comoé', 'comoe',
        'denguélé', 'denguele',
        'gôh', 'goh',
        'lacs', 'marahoué', 'marahoue',
        'montagnes', 'n\'zi', 'nzi',
        'sassandra-marahoué', 'sassandra marahoue',
        'vallée du bandama', 'vallee du bandama',
        'zanzan',
    ]

    SINDEV_TENDER_CONTEXT_ENABLED = True
    SINDEV_TENDER_TERMS = [
        'appel d\'offres', 'appel d offres', 'ao',
        'dossier d\'appel d\'offres', 'dao',
        'appel à manifestation d\'intérêt', 'appel a manifestation d\'interet',
        'manifestation d\'intérêt', 'manifestation d\'interet', 'ami',
        'consultant', 'consultance', 'consulting',
        'prestation', 'prestataire',
        'termes de référence', 'termes de reference', 'tdr', 't.d.r',
        'demande de proposition', 'request for proposal', 'rfp',
        'services de consultant', 'services de consultance',
    ]

    BASIC_AUTH_ENABLED = os.getenv('BASIC_AUTH_ENABLED', '1').lower() not in ('0', 'false', 'no', 'off')
    BASIC_AUTH_MODE = os.getenv('BASIC_AUTH_MODE', 'db').lower()
    BASIC_AUTH_USERNAME = os.getenv('BASIC_AUTH_USERNAME', 'admin@veille.ci')
    BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD', 'admin123')
    BASIC_AUTH_REALM = os.getenv('BASIC_AUTH_REALM', 'Veille Strategique')
    BASIC_AUTH_EXEMPT_PATH_PREFIXES = [
        '/health',
    ]

class DevelopmentConfig(Config):
    """Configuration pour développement"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuration pour production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Configuration pour tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Sélectionner la configuration en fonction de l'environnement
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retourner la configuration active"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
