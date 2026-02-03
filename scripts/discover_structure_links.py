"""Discovery script: find procurement/tender pages for known structures

Usage:
    .\venv\Scripts\python .\scripts\discover_structure_links.py

It will import Backend config and look at TABLEAU_VEILLE_ACTEURS and
STRUCTURES_SCRAPING_TARGETS, crawl the provided URLs, and write
backend/scraping/discovered_targets.json with candidates.
"""
import json
import logging
import os
import re
import sys
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

# Make sure 'backend' is importable
HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'backend'))

try:
    from config import Config
except Exception as e:
    print("Erreur import Config:", e)
    Config = None

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('discover')

TIMEOUT = int(os.getenv('SCRAPING_TIMEOUT', 15))
HEADERS = {'User-Agent': getattr(Config, 'SCRAPING_USER_AGENT', 'Mozilla/5.0')}

INCLUDE_PATTERNS = [
    r'procure', r'tender', r'tenders', r'bid', r'bids', r'rfq', r'rfp', r'eoi', r'appel', r'offre', r'march', r'invitation'
]
INCLUDE_RE = re.compile('|'.join(INCLUDE_PATTERNS), re.IGNORECASE)

EXCLUDE_PARTS = [
    '/blog', '/news', '/press', '/story', '/stories', '/article', '/photo', '/video', '/about', '/contact', '/careers', '/jobs'
]

OUTPUT = os.path.join(ROOT, 'backend', 'scraping', 'discovered_targets.json')


def is_http(url):
    try:
        p = urlparse(url)
        return p.scheme in ('http', 'https')
    except Exception:
        return False


def same_domain(base, candidate):
    try:
        return urlparse(base).netloc.lower() == urlparse(candidate).netloc.lower()
    except Exception:
        return False


def fetch(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        logger.debug(f"fetch failed {url}: {e}")
        return None


def find_candidates_on_page(base_url, soup):
    candidates = set()
    if not soup:
        return candidates

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith('mailto:') or href.startswith('javascript:'):
            continue
        full = urljoin(base_url, href)
        if not is_http(full):
            continue
        if any(p in full.lower() for p in EXCLUDE_PARTS):
            continue
        if not same_domain(base_url, full):
            continue
        text = (a.get_text(' ', strip=True) or '') + ' ' + full
        if INCLUDE_RE.search(text):
            candidates.add(full.split('#')[0].rstrip('/'))
    return candidates


def discover():
    results = {}

    actor_list = getattr(Config, 'TABLEAU_VEILLE_ACTEURS', []) or []
    targets = getattr(Config, 'STRUCTURES_SCRAPING_TARGETS', []) or []

    # Build initial seed dict from both places
    seeds = {}
    for t in targets:
        name = t.get('structure')
        urls = t.get('urls_a_scraper') or []
        if name:
            seeds[name] = set(urls)

    for a in actor_list:
        name = a.get('structure')
        lien = a.get('lien')
        if name and lien:
            seeds.setdefault(name, set()).add(lien)

    logger.info(f"Découverte: {len(seeds)} structures à analyser")

    for name, urlset in seeds.items():
        found = set()
        for u in list(urlset):
            logger.info(f"Visite: {name} -> {u}")
            soup = fetch(u)
            if not soup:
                continue
            # find direct candidates on this page
            cands = find_candidates_on_page(u, soup)
            found.update(cands)
            # try to follow candidates one level deeper
            for cand in list(cands)[:6]:
                logger.info(f"  Exploration rapide: {cand}")
                soup2 = fetch(cand)
                if not soup2:
                    continue
                found.update(find_candidates_on_page(cand, soup2))

        results[name] = sorted(found)

    with open(OUTPUT, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    logger.info(f"Écriture des résultats: {OUTPUT}")
    for k, v in results.items():
        logger.info(f"{k}: {len(v)} liens trouvés")

    return results


if __name__ == '__main__':
    discover()
