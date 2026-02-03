from .base_scraper import BaseScraper
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class DGMPScraper(BaseScraper):
    def __init__(self):
        super().__init__('DGMP')
        self.base_url = 'https://www.admin.sigomap.gouv.ci'
        self.index_paths = ['/','/marches','/appel-offres']

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Démarrage scraping DGMP")
        mots = [m.lower() for m in (mots_cles or [])]
        offres = []

        for path in self.index_paths:
            page = self.recuperer_page(urljoin(self.base_url, path))
            if not page:
                continue

            candidats = page.find_all('a', href=True)
            for a in candidats:
                text = self.extraire_texte(a)
                href = a['href']
                # use effective base if recuperer_page fell back to an alternate host
                base_for_join = getattr(self, '_last_effective_base', None) or self.base_url
                full_url = urljoin(base_for_join, href)
                txt_lower = (text or '').lower()

                common_keywords = ['appel d', 'appel', 'offre', 'marché', 'avis', 'appel d\'offres', 'procurement']
                matches_kw = any(k in txt_lower for k in common_keywords) or (mots and any(k in txt_lower for k in mots))

                if matches_kw:
                    mots_trouves = [k for k in mots if k in txt_lower]
                    offres.append(self.creer_offre(
                        titre=text or full_url,
                        source=self.source_nom,
                        url=full_url,
                        description='',
                        mots_cles_trouves=mots_trouves
                    ))

        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres candidates trouvées")
        return offres
