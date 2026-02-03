from .base_scraper import BaseScraper
import logging
from urllib.parse import urljoin, urlparse
import re
from dateutil import parser as date_parser

from config import Config

logger = logging.getLogger(__name__)


class StructuresLinksScraper(BaseScraper):
    def __init__(self):
        super().__init__('STRUCTURES')
        self.targets = getattr(Config, 'STRUCTURES_SCRAPING_TARGETS', [])
        self.sindev_focus_enabled = bool(getattr(Config, 'SINDEV_FOCUS_ENABLED', True))
        self.sindev_focus_terms = [t.lower() for t in getattr(Config, 'SINDEV_FOCUS_TERMS', []) if t]
        self.sindev_ci_only = bool(getattr(Config, 'SINDEV_CI_ONLY', False))
        self.sindev_ci_terms = [t.lower() for t in getattr(Config, 'SINDEV_CI_TERMS', []) if t]
        self.sindev_ci_geo_terms = [t.lower() for t in getattr(Config, 'SINDEV_CI_GEO_TERMS', []) if t]

    def _is_http_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            u = urlparse(url)
            return u.scheme in ('http', 'https')
        except Exception:
            return False

    def _matches_ci_terms(self, text: str) -> bool:
        if not text:
            return False
        hay = text.lower()

        context_patterns = [
            r"(?:lieu\s*d['’]?ex[ée]cution|lieu\s*de\s*mission|lieu\s*d'intervention|zone\s*d'intervention|pays\s*d'ex[ée]cution|pays\s*de\s*mission)\s*[:\-–]?\s*(?:republique\s*de\s*)?(?:c[oô]te\s*d['’]?ivoire|ivory\s*coast|cotedivoire|cote\s*divoire)",
            r"(?:duty\s*station|location|place\s*of\s*(?:assignment|work)|country\s*of\s*(?:assignment|performance)|implementation\s*(?:country|location))\s*[:\-–]?\s*(?:republic\s*of\s*)?(?:c[oô]te\s*d['’]?ivoire|ivory\s*coast|cotedivoire|cote\s*divoire)",
        ]

        for pat in context_patterns:
            if re.search(pat, hay, flags=re.IGNORECASE):
                return True

        for term in (self.sindev_ci_terms + self.sindev_ci_geo_terms):
            t = (term or '').strip().lower()
            if not t:
                continue
            if len(t) <= 3:
                # Réduire le bruit: matcher CI/CIV comme mot entier
                if re.search(rf"\b{re.escape(t)}\b", hay, flags=re.IGNORECASE):
                    return True
            else:
                if t in hay:
                    return True
        return False

    def _is_ci_domain(self, url: str) -> bool:
        if not url:
            return False
        try:
            u = urlparse(url)
            host = (u.netloc or '').lower()
            return host.endswith('.ci') or '.ci:' in host
        except Exception:
            return False

    def _is_same_domain(self, base_url: str, candidate_url: str) -> bool:
        try:
            b = urlparse(base_url)
            c = urlparse(candidate_url)
            if not b.netloc or not c.netloc:
                return True
            return b.netloc.lower() == c.netloc.lower()
        except Exception:
            return True

    def _parse_deadline_from_soup(self, soup):
        if not soup:
            return None

        for t in soup.find_all('time'):
            if t and t.has_attr('datetime'):
                try:
                    dt = date_parser.parse(t['datetime'])
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(tz=None).replace(tzinfo=None)
                    return dt
                except Exception:
                    pass

        text = soup.get_text(' ', strip=True)
        if not text:
            return None

        triggers = r"(?:date\s+limite|date\s+de\s+cl[oô]ture|cl[oô]ture|deadline|closing\s+date|submission\s+deadline|date\s+limite\s+de\s+soumission|d[eé]p[oô]t\s+des\s+offres|date\s+de\s+d[eé]p[oô]t)"

        patterns = [
            # 15/02/2026, 15-02-2026, 15.02.2026 (+ heure optionnelle)
            rf"{triggers}\s*[:\-–]?\s*([0-9]{{1,2}}[\./\-][0-9]{{1,2}}[\./\-][0-9]{{2,4}}(?:\s*(?:[àa]|a)?\s*[0-9]{{1,2}}(?:[:h][0-9]{{0,2}})?(?:\s*(?:min|mn)?)?)?)",
            # 2026-02-15, 2026/02/15 (+ heure optionnelle)
            rf"{triggers}\s*[:\-–]?\s*([0-9]{{4}}[\./\-][0-9]{{1,2}}[\./\-][0-9]{{1,2}}(?:\s*(?:[àa]|a)?\s*[0-9]{{1,2}}(?:[:h][0-9]{{0,2}})?(?:\s*(?:min|mn)?)?)?)",
            # 15 février 2026 (+ heure optionnelle)
            rf"{triggers}\s*[:\-–]?\s*([0-9]{{1,2}}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{{2,4}}(?:\s*(?:[àa]|a)?\s*[0-9]{{1,2}}(?:[:h][0-9]{{0,2}})?(?:\s*(?:min|mn)?)?)?)",
        ]

        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                try:
                    dt = date_parser.parse(m.group(1), dayfirst=True, fuzzy=True)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(tz=None).replace(tzinfo=None)
                    return dt
                except Exception:
                    continue

        return None

    def _parse_offer_page(self, url):
        page = self.recuperer_page(url)
        if not page:
            return None

        titre = self.extraire_texte(page.find('h1')) or (page.title.string.strip() if page.title and page.title.string else url)

        description = ''
        meta_desc = page.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.has_attr('content'):
            description = (meta_desc['content'] or '').strip()
        if not description:
            main = page.find('main') or page.find('article') or page
            p = main.find('p') if main else None
            description = self.extraire_texte(p)

        date_clot = self._parse_deadline_from_soup(page)

        return {
            'titre': titre,
            'description': description or '',
            'date_cloturation': date_clot,
            'url': url,
        }

    def scrape(self, mots_cles=None):
        logger.info(f"[{self.source_nom}] Démarrage scraping (structures)")

        mots = [m.lower() for m in (mots_cles or []) if m]
        offres = []

        common_keywords = [
            'appel',
            "appel d'offres",
            'offre',
            'marché',
            'marches',
            'avis',
            'manifestation',
            'tender',
            'tenders',
            'procurement',
            'rfq',
            'rfp',
            'eoi',
            'expression of interest',
            'invitation',
        ]

        # Exclure des chemins typiquement "contenu" (actualités, stories, etc.)
        exclude_url_parts = [
            '/blog', '/news', '/press', '/story', '/stories', '/article', '/photo', '/video',
            '/climate', '/report', '/publications', '/about', '/contact', '/careers',
            '/jobs', '/media', '/events'
        ]

        include_url_parts = [
            'procurement', 'tender', 'tenders', 'bid', 'bids', 'rfq', 'rfp', 'eoi',
            'expression-of-interest', 'invitation', 'appel', 'offre', 'march', 'avis'
        ]

        for target in self.targets:
            structure = (target or {}).get('structure') or (target or {}).get('nom')
            urls = (target or {}).get('urls_a_scraper') or []

            if not structure or not urls:
                continue

            for page_url in urls:
                soup = self.recuperer_page(page_url)
                if not soup:
                    continue

                candidats = soup.find_all('a', href=True)
                for a in candidats:
                    text = self.extraire_texte(a)
                    href = a.get('href')
                    if not href:
                        continue

                    base_for_join = getattr(self, '_last_effective_base', None) or page_url
                    full_url = urljoin(base_for_join, href)

                    if full_url.startswith('mailto:') or full_url.startswith('javascript:'):
                        continue
                    if not self._is_http_url(full_url):
                        continue
                    if not self._is_same_domain(page_url, full_url):
                        continue

                    url_lower = full_url.lower()
                    if any(p in url_lower for p in exclude_url_parts):
                        continue

                    hay = f"{text} {full_url}".strip().lower()
                    matches_common = any(k in hay for k in common_keywords)
                    matches_mots = bool(mots) and any(k in hay for k in mots)
                    matches_url = any(k in url_lower for k in include_url_parts)

                    if not (matches_url and (matches_common or matches_mots)):
                        continue

                    details = None
                    try:
                        details = self._parse_offer_page(full_url)
                    except Exception:
                        details = None

                    details_text = ''
                    if details:
                        details_text = f"{details.get('titre','')} {details.get('description','')}".lower()

                    matches_focus = False
                    if self.sindev_focus_enabled and self.sindev_focus_terms:
                        matches_focus = any(t in hay or t in details_text for t in self.sindev_focus_terms)

                    if self.sindev_ci_only and self.sindev_ci_terms:
                        matches_ci = (
                            self._matches_ci_terms(hay)
                            or self._matches_ci_terms(details_text)
                            or self._is_ci_domain(full_url)
                        )
                        if not matches_ci:
                            continue

                    # Filtre SinDev: garder si mots-clés ou focus SinDev
                    if self.sindev_focus_enabled and not (matches_mots or matches_focus):
                        continue

                    mots_trouves = [k for k in mots if k in hay]
                    offre = self.creer_offre(
                        titre=(details.get('titre') if details else None) or (text or full_url),
                        source=self.source_nom,
                        url=full_url,
                        description=(details.get('description') if details else '') or '',
                        date_clot=(details.get('date_cloturation') if details else None),
                        type_offre='Offre',
                        partenaire=structure,
                        mots_cles_trouves=mots_trouves,
                    )
                    offres.append(offre)

        offres = self.nettoyer_offres_doublons(offres)
        logger.info(f"[{self.source_nom}] {len(offres)} offres candidates trouvées")
        return offres
