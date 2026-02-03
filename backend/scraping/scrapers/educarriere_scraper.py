"""
Scraper pour EduCarrière (plateforme d'emploi et formation)
"""

from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class EduCarriereScraper(BaseScraper):
    """Scraper pour les offres EduCarrière"""
    
    def __init__(self):
        super().__init__('EduCarrière')
        self.base_url = 'https://educarriere.ci'
    
    def scrape(self, mots_cles=None):
        """Scraper les offres d'emploi et formations EduCarrière"""
        logger.info(f"[{self.source_nom}] Début du scraping")
        offres = []
        
        # Endpoints pour différents types d'offres
        endpoints = [
            '/offres-emploi',
            '/appels-offres',
            '/formations',
            '/bourses',
        ]
        
        for endpoint in endpoints:
            url = self.base_url + endpoint
            soup = self.recuperer_page(url)
            
            if soup:
                # Adapter selon la structure réelle d'EduCarrière
                offre_elements = soup.find_all('div', class_='offre-card')
                
                for element in offre_elements:
                    titre = self.extraire_texte(element.find('h3', class_='offre-titre'))
                    lien = element.find('a', href=True)
                    url_offre = lien['href'] if lien else None
                    organisation = self.extraire_texte(element.find('span', class_='organisation'))
                    description = self.extraire_texte(element.find('p', class_='offre-description'))
                    date_pub = self.extraire_texte(element.find('span', class_='date-pub'))
                    
                    if titre and url_offre:
                        # Déterminer le type d'offre
                        type_offre = self._determiner_type(endpoint, titre, description)
                        
                        mots_trouves = self.matcher_mots_cles(
                            f"{titre} {description} {organisation}",
                            mots_cles
                        )
                        
                        offre = self.creer_offre(
                            titre=titre,
                            source=self.source_nom,
                            url=url_offre,
                            description=description,
                            partenaire=organisation,
                            type_offre=type_offre,
                            mots_cles_trouves=mots_trouves
                        )
                        offres.append(offre)
        
        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres trouvées")
        return offres
    
    def _determiner_type(self, endpoint, titre, description):
        """Déterminer le type d'offre basé sur l'endpoint et le contenu"""
        types = {
            '/offres-emploi': 'Offre d\'emploi',
            '/appels-offres': 'Appel d\'offres',
            '/formations': 'Formation',
            '/bourses': 'Bourse d\'études',
        }
        return types.get(endpoint, 'Offre')
