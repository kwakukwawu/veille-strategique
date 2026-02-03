"""
Gestion centralisée des mots-clés pour le scraping
Les mots-clés sont utilisés par tous les scrapers pour filtrer les offres
"""

from database.models import MotsCles, db

class KeywordManager:
    """Gestionnaire des mots-clés"""
    
    # Cache en mémoire pour les performances
    _cache = {}
    _cache_par_categorie = {}
    
    @staticmethod
    def obtenir_tous_mots_cles():
        """Récupérer tous les mots-clés actifs"""
        mots = MotsCles.query.filter_by(actif=True).all()
        return [m.mot for m in mots]
    
    @staticmethod
    def obtenir_par_categorie(categorie):
        """Récupérer les mots-clés d'une catégorie"""
        mots = MotsCles.query.filter_by(categorie=categorie, actif=True).all()
        return [m.mot for m in mots]
    
    @staticmethod
    def obtenir_categories():
        """Obtenir toutes les catégories de mots-clés"""
        categories = db.session.query(MotsCles.categorie).distinct().all()
        return [c[0] for c in categories if c[0]]

    @staticmethod
    def normaliser_mot(mot: str) -> str:
        if mot is None:
            return ''
        m = str(mot).strip()
        m = m.replace('’', "'")
        m = m.replace('“', '"').replace('”', '"')
        m = m.replace('\u00A0', ' ')
        m = m.strip(' ;,\t\r\n')
        # collapse whitespace
        m = ' '.join(m.split())
        return m
    
    @staticmethod
    def ajouter_mot_cle(mot, categorie='Général'):
        """Ajouter un nouveau mot-clé"""
        mot_n = KeywordManager.normaliser_mot(mot)
        if not mot_n:
            return False
        if not MotsCles.query.filter_by(mot=mot_n).first():
            nouveau_mot = MotsCles(mot=mot_n, categorie=categorie)
            db.session.add(nouveau_mot)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def supprimer_mot_cle(mot_id):
        """Supprimer un mot-clé (soft delete)"""
        mot = MotsCles.query.get(mot_id)
        if mot:
            mot.actif = False
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def activer_mot_cle(mot_id):
        """Réactiver un mot-clé"""
        mot = MotsCles.query.get(mot_id)
        if mot:
            mot.actif = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def lister_tous():
        """Lister tous les mots-clés avec détails"""
        mots = MotsCles.query.all()
        return [m.to_dict() for m in mots]
    
    @staticmethod
    def chercher_par_nom(query):
        """Chercher des mots-clés par nom"""
        query = KeywordManager.normaliser_mot(query)
        mots = MotsCles.query.filter(
            MotsCles.mot.ilike(f'%{query}%'),
            MotsCles.actif == True
        ).all()
        return [m.mot for m in mots]
