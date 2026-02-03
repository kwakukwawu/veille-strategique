from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class UEScraper(BaseScraper):
    def __init__(self):
        super().__init__('UE')
        self.base_url = 'https://europa.eu'

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Scraper stub exécuté")
        return []
