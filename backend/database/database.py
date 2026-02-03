"""
Initialisation et gestion de la base de données
Crée les tables et gère les sessions
"""

from flask_sqlalchemy import SQLAlchemy
from .models import db


def get_default_sources_data():
    return [
        ('GIZ', 'https://giz.de', 'giz'),
        ('ENABEL', 'https://enabel.be', 'enabel'),
        ('ANABEL', 'https://anabel.ci', 'anabel'),
        ('MINADER', 'https://minader.ci', 'minader'),
        ('FIRCA', 'https://firca.ci', 'firca'),
        ('ANADER', 'https://anader.ci', 'anader'),
        ('PAM', 'https://wfp.org', 'pam'),
        ('FAO', 'https://fao.org', 'fao'),
        ('UE', 'https://europa.eu', 'ue'),
        ('AFD', 'https://afd.fr', 'afd'),
        ('PNUD', 'https://undp.org', 'pnud'),
        ('Banque Mondiale', 'https://worldbank.org', 'worldbank'),
        ('BAD', 'https://afdb.org', 'bad'),
        ('EduCarriere', 'https://educarriere.ci', 'educarriere'),
        ('DGMP', 'https://www.admin.sigomap.gouv.ci', 'dgmp'),
        ('Fraternité Matin', 'https://www.fratmat.info/', 'structures'),
        ('Marchés Publics CI (DGMP)', 'https://www.marchespublics.ci/appel_offre', 'structures'),
        ('ARCOP', 'https://arcop.ci/documentation/avis/avis-dappel-doffres/', 'structures'),
        ('AGEROUTE CI', 'https://ageroute.ci/appels-d-offres/avis-d-appel-d-offres-de-travaux', 'structures'),
        ('ANSUT', 'https://ansut.ci/recrutement/appel-a-prestataire/', 'structures'),
        ('Fonds d’Entretien Routier (FER)', 'https://www.fer.ci/appels_offre/procedures', 'structures'),
        ('STRUCTURES', '', 'structures')
    ]

def init_db(app):
    """Initialiser la base de données avec Flask.

    Note: L'extension `db` doit être initialisée par l'application
    (ex. `db.init_app(app)`) **avant** d'appeler `init_db`.
    """
    # Ne pas appeler db.init_app(app) ici pour éviter une double initialisation
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        print("Base de données initialisée")
        
        # Ajouter les mots-clés par défaut s'ils n'existent pas
        _initialiser_donnees_par_defaut()

def _initialiser_donnees_par_defaut():
    """Remplir les données de départ dans la base"""
    from .models import MotsCles, Source
    
    # Mots-clés par défaut - Chaînes de valeur agricoles
    chaines_valeur = [
        'Anacarde', 'Cacao', 'Agroforesterie', 'Agriculture', 'Développement rural',
        'Environnement', 'Biodiversité', 'Changement climatique', 'Foncier rural',
        'Semences améliorées', 'Intrants agricoles', 'Économie rurale', 'Partenariats public-privé',
        'Développement local', 'Entrepreneuriat', 'Plans de développement', 'Coopératives',
        'Renforcement de capacités', 'Autonomisation des femmes', 'Emploi des jeunes',
        'Inclusion financière', 'Économie circulaire', 'Microfinance'
    ]
    
    for mot in chaines_valeur:
        if not MotsCles.query.filter_by(mot=mot).first():
            db.session.add(MotsCles(mot=mot, categorie='Chaîne de valeur'))
    
    # Types d'offres
    types_offres = [
        'Appel d\'offres', 'Avis de manifestation d\'intérêt', 'Contrat de prestation',
        'Études de faisabilité', 'Suivi-évaluation', 'Formation', 'Expertise technique',
        'Audit externe', 'Appui institutionnel', 'Sensibilisation', 'Assistance technique',
        'Projet pilote'
    ]
    
    for mot in types_offres:
        if not MotsCles.query.filter_by(mot=mot).first():
            db.session.add(MotsCles(mot=mot, categorie='Type d\'offre'))

    # Thèmes et mots-clés supplémentaires fournis par l'utilisateur
    autres_mots = [
        'Anacarde', 'Économie rurale', 'Partenariats public-privé', 'Développement local',
        'Entrepreneuriat', 'Plans de développement', 'Coopératives', 'Renforcement de capacités',
        'Autonomisation des femmes', 'Emploi des jeunes', 'Inclusion financière', 'Économie circulaire',
        'Microfinance', 'Appel d’offres', 'Avis de manifestation d’intérêt', 'Contrat de prestation',
        'Études de faisabilité', 'Suivi-évaluation', 'Formation', 'Expertise technique', 'Audit externe',
        'Appui institutionnel', 'Sensibilisation', 'Assistance technique', 'Projet pilote', 'Agriculture',
        'Agroforesterie', 'Développement rural', 'Environnement', 'Biodiversité', 'Changement climatique',
        'Foncier rural', 'Semences améliorées', 'Intrants agricoles', 'Cacao'
    ]
    for mot in autres_mots:
        if not MotsCles.query.filter_by(mot=mot).first():
            db.session.add(MotsCles(mot=mot, categorie='Thème'))
    
    # Partenaires
    partenaires = [
        'GIZ', 'ENABEL', 'ANABEL', 'FIRCA', 'ANADER', 'MINADER', 'PAM', 'FAO', 'UE',
        'AFD', 'PNUD', 'Banque Mondiale', 'BAD', 'EduCarriere', 'DGMP'
    ]
    
    for mot in partenaires:
        if not MotsCles.query.filter_by(mot=mot).first():
            db.session.add(MotsCles(mot=mot, categorie='Partenaire'))
    
    sources_data = get_default_sources_data()
    
    for nom, url, type_scraper in sources_data:
        if not Source.query.filter_by(nom=nom).first():
            db.session.add(Source(nom=nom, url_base=url, type_scraper=type_scraper))

    # Créer un utilisateur admin de démonstration si inexistant (mot de passe hashé)
    try:
        from werkzeug.security import generate_password_hash
        from .models import Utilisateur
        if not Utilisateur.query.filter_by(email='admin@veille.ci').first():
            admin = Utilisateur(
                email='admin@veille.ci',
                nom_complet='Administrateur',
                mot_de_passe_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            print('Utilisateur admin créé (admin@veille.ci / admin123)')
    except Exception:
        # Si werkzeug non disponible pour une raison quelconque, ignorer la création
        pass
    
    db.session.commit()
    print("Données par défaut chargées")

def get_db_stats():
    """Obtenir les statistiques de la base"""
    from .models import Offre, MotsCles, Source
    
    return {
        'total_offres': Offre.query.count(),
        'offres_actives': Offre.query.filter_by(actif=True).count(),
        'total_mots_cles': MotsCles.query.count(),
        'total_sources': Source.query.count(),
        'sources_actives': Source.query.filter_by(actif=True).count(),
    }
