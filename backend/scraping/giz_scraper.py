"""
Scraper pour GIZ (Deutsche Gesellschaft für Internationale Zusammenarbeit)
"""

from scraping.scrapers.base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class GIZScraper(BaseScraper):
    """Scraper pour les offres GIZ (stub/exemple)"""

    def __init__(self):
        super().__init__('GIZ')
        self.base_url = 'https://www.giz.de'
        self.search_endpoints = [
            '/en/worldwide/projects-and-programmes',
            '/en/worldwide/job-offers',
            '/en/worldwide/tenders',
        ]

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Début du scraping (stub)")
        offres = []

        for endpoint in self.search_endpoints:
            url = self.base_url + endpoint
            soup = self.recuperer_page(url)
            if not soup:
                continue

            # Exemple générique : trouver liens et titres (doit être adapté au site réel)
            for a in soup.find_all('a', href=True):
                titre = self.extraire_texte(a)
                lien = a['href']
                if not titre or not lien:
                    continue

                if lien.startswith('/'):
                    lien = self.base_url + lien

                mots_trouves = self.matcher_mots_cles(f"{titre}", mots_cles)

                offre = self.creer_offre(
                    titre=titre,
                    source=self.source_nom,
                    url=lien,
                    description='(extrait automatique)',
                    mots_cles_trouves=mots_trouves
                )
                offres.append(offre)

        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres trouvées (stub)")
        return offres