from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class MinaderScraper(BaseScraper):
    def __init__(self):
        super().__init__('MINADER')
        self.base_url = 'https://minader.ci'

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Scraper stub exécuté")
        return []
