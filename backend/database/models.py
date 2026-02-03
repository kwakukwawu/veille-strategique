"""
Modèles SQLAlchemy pour la base de données
Définit les tables et relations
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Offre(db.Model):
    """Modèle pour stocker les offres/appels trouvés"""
    __tablename__ = 'offres'
    
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    source = db.Column(db.String(100), nullable=False)  # GIZ, ENABEL, etc.
    url = db.Column(db.String(500), unique=True, nullable=False)
    date_publication = db.Column(db.DateTime)
    date_cloturation = db.Column(db.DateTime)
    type_offre = db.Column(db.String(100))  # 'Appel d\'offres', 'Manifestation d\'intérêt', etc.
    partenaire = db.Column(db.String(200))  # GIZ, ENABEL, PAM, FAO, etc.
    mots_cles = db.Column(db.String(500))  # Mots-clés détectés (séparés par virgule)
    date_scrape = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actif = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convertir en dictionnaire pour JSON"""
        return {
            'id': self.id,
            'titre': self.titre,
            'description': self.description,
            'source': self.source,
            'url': self.url,
            'date_publication': self.date_publication.isoformat() if self.date_publication else None,
            'date_cloturation': self.date_cloturation.isoformat() if self.date_cloturation else None,
            'type_offre': self.type_offre,
            'partenaire': self.partenaire,
            'mots_cles': self.mots_cles,
            'date_scrape': self.date_scrape.isoformat(),
        }

class MotsCles(db.Model):
    """Modèle pour gérer les mots-clés de recherche"""
    __tablename__ = 'mots_cles'
    
    id = db.Column(db.Integer, primary_key=True)
    mot = db.Column(db.String(200), unique=True, nullable=False)
    categorie = db.Column(db.String(100))  # 'Chaîne de valeur', 'Type d\'offre', 'Partenaire', etc.
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mot': self.mot,
            'categorie': self.categorie,
            'actif': self.actif
        }

class Source(db.Model):
    """Modèle pour gérer les sources de scraping"""
    __tablename__ = 'sources'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    url_base = db.Column(db.String(500))
    type_scraper = db.Column(db.String(100))  # 'giz', 'enabel', 'gov', 'un', etc.
    actif = db.Column(db.Boolean, default=True)
    derniere_execusion = db.Column(db.DateTime)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'url_base': self.url_base,
            'type_scraper': self.type_scraper,
            'actif': self.actif,
            'derniere_execusion': self.derniere_execusion.isoformat() if self.derniere_execusion else None
        }

class Utilisateur(db.Model):
    """Modèle pour les utilisateurs (admin, lecteur)"""
    __tablename__ = 'utilisateurs'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    nom_complet = db.Column(db.String(200))
    mot_de_passe_hash = db.Column(db.String(255))
    role = db.Column(db.String(50), default='lecteur')  # 'admin', 'lecteur', 'editeur'
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nom_complet': self.nom_complet,
            'role': self.role,
            'actif': self.actif
        }

class LogScraping(db.Model):
    """Modèle pour tracer l'historique du scraping"""
    __tablename__ = 'logs_scraping'
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), nullable=False)
    date_execution = db.Column(db.DateTime, default=datetime.utcnow)
    nombre_offres_trouvees = db.Column(db.Integer, default=0)
    nombre_offres_nouvelles = db.Column(db.Integer, default=0)
    statut = db.Column(db.String(50))  # 'succes', 'erreur', 'partiel'
    message_erreur = db.Column(db.Text)
    temps_execution = db.Column(db.Float)  # en secondes
    
    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'date_execution': self.date_execution.isoformat(),
            'nombre_offres_trouvees': self.nombre_offres_trouvees,
            'nombre_offres_nouvelles': self.nombre_offres_nouvelles,
            'statut': self.statut,
            'temps_execution': self.temps_execution
        }
