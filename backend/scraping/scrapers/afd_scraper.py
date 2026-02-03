from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class AFDScraper(BaseScraper):
    def __init__(self):
        super().__init__('AFD')
        self.base_url = 'https://www.afd.fr'

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Scraper stub exécuté")
        return []
