"""
Scraper pour les organismes des Nations Unies (FAO, PAM, PNUD, etc.)
"""

from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class UNScraper(BaseScraper):
    """Scraper pour les offres des agences de l'ONU"""
    
    def __init__(self):
        super().__init__('Nations Unies')
        self.sources = {
            'FAO': 'https://www.fao.org/tenders',
            'PAM': 'https://www.wfp.org/tenders',
            'PNUD': 'https://www.undp.org/tenders',
        }
    
    def scrape(self, mots_cles=None):
        """Scraper les appels d'offres des agences ONU"""
        logger.info(f"[{self.source_nom}] Début du scraping")
        offres = []
        
        for agence, url_base in self.sources.items():
            soup = self.recuperer_page(url_base)
            
            if soup:
                # Chercher les éléments de liste
                articles = soup.find_all('div', class_='tender-item')
                
                for article in articles:
                    titre = self.extraire_texte(article.find('h3'))
                    lien = article.find('a', href=True)
                    url_offre = lien['href'] if lien else None
                    date_str = self.extraire_texte(article.find('span', class_='date'))
                    description = self.extraire_texte(article.find('p'))
                    
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
                            partenaire=agence,
                            type_offre='Appel d\'offres',
                            mots_cles_trouves=mots_trouves
                        )
                        offres.append(offre)
        
        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres trouvées")
        return offres
