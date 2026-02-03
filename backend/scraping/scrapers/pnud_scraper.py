from .base_scraper import BaseScraper
import logging
from urllib.parse import urljoin
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

class PNUDScraper(BaseScraper):
    def __init__(self):
        super().__init__('PNUD')
        self.base_url = 'https://www.undp.org'
        # Éviter la page d'accueil (trop de bruit: actualités, stories, etc.)
        self.index_paths = ['/procurement', '/content/undp/en/home/procurement.html']

    def _parse_offer_page(self, url):
        page = self.recuperer_page(url)
        if not page:
            return None

        titre = self.extraire_texte(page.find('h1')) or (page.title.string if page.title else url)

        meta_desc = page.find('meta', attrs={'name': 'description'})
        description = self.extraire_texte(meta_desc) if meta_desc else None
        if not description:
            article = page.find('article') or page.find('main')
            if article:
                p = article.find('p')
                description = self.extraire_texte(p)

        date_pub = None
        time_tag = page.find('time')
        if time_tag and time_tag.has_attr('datetime'):
            try:
                date_pub = date_parser.parse(time_tag['datetime'])
            except Exception:
                pass

        partner = None
        publisher = page.find('meta', attrs={'name': 'author'}) or page.find('meta', attrs={'property': 'og:site_name'})
        if publisher and publisher.has_attr('content'):
            partner = publisher['content']

        return {
            'titre': titre,
            'description': description or '',
            'date_publication': date_pub,
            'partenaire': partner or self.source_nom,
            'url': url
        }

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Démarrage scraping PNUD")
        mots = [m.lower() for m in (mots_cles or [])]
        offres = []
        vus = set()

        exclude_url_parts = [
            '/blog', '/news', '/press', '/story', '/stories', '/article', '/photo', '/video',
            '/climate', '/equator', '/report', '/publications', '/about', '/contact'
        ]

        include_url_parts = [
            'procurement-notices', '/procurement', 'tender', 'tenders', 'bid', 'bids',
            'rfq', 'rfp', 'eoi', 'expression-of-interest', 'invitation'
        ]

        for path in self.index_paths:
            page = self.recuperer_page(urljoin(self.base_url, path))
            if not page:
                continue

            candidats = page.find_all('a', href=True)
            for a in candidats:
                text = self.extraire_texte(a)
                href = a['href']
                full_url = urljoin(self.base_url, href)
                if full_url in vus:
                    continue
                vus.add(full_url)

                if full_url.startswith('mailto:') or full_url.startswith('#'):
                    continue

                url_lower = full_url.lower()
                if any(p in url_lower for p in exclude_url_parts):
                    continue

                txt_lower = (text or '').lower()
                common_keywords = ['procurement', 'tender', 'opportunity', 'call', 'contract', 'bid', 'procure']
                matches_kw = any(k in txt_lower for k in common_keywords) or (mots and any(k in txt_lower for k in mots))
                matches_url = any(p in url_lower for p in include_url_parts)

                if not (matches_url or matches_kw):
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
                    logger.exception(f"Erreur parsing PNUD page {full_url}: {e}")

        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres candidates trouvées")
        return offres
