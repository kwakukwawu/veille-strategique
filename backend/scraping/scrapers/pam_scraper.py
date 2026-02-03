from .base_scraper import BaseScraper
import logging
from urllib.parse import urljoin
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

class PAMScraper(BaseScraper):
    def __init__(self):
        super().__init__('PAM')
        self.base_url = 'https://www.wfp.org'
        self.index_path = '/'

    def _parse_offer_page(self, url):
        """Suivre la page de l'offre et extraire titre, description, date."""
        page = self.recuperer_page(url)
        if not page:
            return None

        # Titre
        titre = self.extraire_texte(page.find('h1')) or page.title.string if page.title else None

        # Description: meta description ou premier paragraphe dans main/article
        meta_desc = page.find('meta', attrs={'name': 'description'})
        description = self.extraire_texte(meta_desc) if meta_desc else None
        if not description:
            article = page.find('article') or page.find('main')
            if article:
                p = article.find('p')
                description = self.extraire_texte(p)

        # Date: chercher les balises <time> ou mots 'date' dans le DOM
        date_pub = None
        time_tag = page.find('time')
        if time_tag and time_tag.has_attr('datetime'):
            try:
                date_pub = date_parser.parse(time_tag['datetime'])
            except Exception:
                pass
        elif time_tag:
            try:
                date_pub = date_parser.parse(self.extraire_texte(time_tag))
            except Exception:
                pass

        # Partenaire / organisation
        partner = None
        publisher = page.find('meta', attrs={'name': 'author'}) or page.find('meta', attrs={'property': 'og:site_name'})
        if publisher and publisher.has_attr('content'):
            partner = publisher['content']

        return {
            'titre': titre or url,
            'description': description or '',
            'date_publication': date_pub,
            'partenaire': partner or self.source_nom,
            'url': url
        }

    def scrape(self, mots_cles=None):
        """Scraper PAM: suivre liens trouvés sur la page d'accueil et extraire détails."""
        logger.info(f"[{self.source_nom}] Démarrage scraping PAM")
        page = self.recuperer_page(urljoin(self.base_url, self.index_path))
        if not page:
            return []

        candidats = page.find_all('a', href=True)
        common_keywords = ['appel', 'tender', 'procurement', 'opportunity', 'bid', 'invitation', 'offre']
        mots = [m.lower() for m in (mots_cles or [])]
        offres = []
        vus = set()

        for a in candidats:
            text = self.extraire_texte(a)
            href = a['href']
            full_url = urljoin(self.base_url, href)
            if full_url in vus:
                continue
            vus.add(full_url)

            txt_lower = (text or '').lower()
            matches_kw = any(k in txt_lower for k in common_keywords) or (mots and any(k in txt_lower for k in mots))
            # Skip anchors and mailto
            if not matches_kw or full_url.startswith('mailto:') or full_url.startswith('#'):
                continue

            try:
                details = self._parse_offer_page(full_url)
                if not details:
                    continue

                mots_trouves = [k for k in mots if k in (text or '').lower() or k in (details.get('description') or '').lower()]
                offres.append(self.creer_offre(
                    titre=details['titre'],
                    source=self.source_nom,
                    url=details['url'],
                    description=details['description'],
                    date_pub=details.get('date_publication'),
                    partenaire=details.get('partenaire'),
                    mots_cles_trouves=mots_trouves
                ))
            except Exception as e:
                logger.exception(f"Erreur parsing PAM page {full_url}: {e}")

        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres candidates trouvées")
        return offres
