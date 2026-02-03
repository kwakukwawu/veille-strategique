from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class AnaderScraper(BaseScraper):
    def __init__(self):
        super().__init__('ANADER')
        self.base_url = 'https://anader.ci'

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Scraper stub exécuté")
        return []
