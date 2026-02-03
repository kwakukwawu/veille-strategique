"""
Scraper pour GIZ (Deutsche Gesellschaft für Internationale Zusammenarbeit)
"""

from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class GIZScraper(BaseScraper):
    """Scraper pour les offres GIZ"""
    
    def __init__(self):
        super().__init__('GIZ')
        self.base_url = 'https://www.giz.de'
        self.search_endpoints = [
            '/en/worldwide/projects-and-programmes',
            '/en/worldwide/job-offers',
            '/en/worldwide/tenders'
        ]
    
    def scrape(self, mots_cles=None):
        """
        Scraper les offres de GIZ
        
        Note: Dans un vrai projet, adapter selon la structure réelle du site GIZ
        """
        logger.info(f"[{self.source_nom}] Début du scraping")
        offres = []
        
        # Exemple simple (à adapter à la structure réelle)
        for endpoint in self.search_endpoints:
            url = self.base_url + endpoint
            soup = self.recuperer_page(url)
            
            if soup:
                # Chercher les éléments contenant les offres
                # La structure réelle dépend de la page GIZ
                articles = soup.find_all('article', class_='offer')
                
                for article in articles:
                    titre = self.extraire_texte(article.find('h2'))
                    lien = article.find('a', href=True)
                    url_offre = lien['href'] if lien else None
                    description = self.extraire_texte(article.find('p', class_='description'))
                    
                    if titre and url_offre:
                        mots_trouves = self.matcher_mots_cles(
                            f"{titre} {description}", 
                            mots_cles
                        )
                        
                        offre = self.creer_offre(
                            titre=titre,
                            source=self.source_nom,
                            url=url_offre,
                            description=description,
                            mots_cles_trouves=mots_trouves
                        )
                        offres.append(offre)
        
        # Nettoyer les doublons
        offres = self.nettoyer_offres_doublons(offres)
        
        logger.info(f"[{self.source_nom}] {len(offres)} offres trouvées")
        return offres
