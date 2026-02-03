from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class EnabelScraper(BaseScraper):
    def __init__(self):
        super().__init__('ENABEL')
        self.base_url = 'https://www.enabel.be'

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Scraper stub exécuté")
        return []
