"""Import discovered targets into the `sources` table and run the `structures` scraper once.

Usage:
    .\venv\Scripts\python .\scripts\import_and_run_structures.py
"""
import json
import os
import logging
import sys
# Ensure project root is importable (when running via system python)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Also ensure backend folder is importable as top-level to satisfy local imports
BACKEND_DIR = os.path.join(ROOT, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app
from database.models import db, Source
from scraping.scheduler import scheduler

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('importer')

APP = create_app()

DISCOVERED = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'backend', 'scraping', 'discovered_targets.json')


def import_sources():
    with APP.app_context():
        if not os.path.exists(DISCOVERED):
            logger.error(f"Fichier introuvable: {DISCOVERED}")
            return
        with open(DISCOVERED, 'r', encoding='utf-8') as fh:
            data = json.load(fh) or {}

        created = 0
        updated = 0
        for name, urls in data.items():
            if not urls:
                continue
            first_url = urls[0]
            src = Source.query.filter_by(nom=name).first()
            if src:
                if not src.url_base:
                    src.url_base = first_url
                    updated += 1
                else:
                    # do not overwrite existing url_base by default
                    pass
            else:
                new = Source(nom=name, url_base=first_url, type_scraper=None, actif=True)
                db.session.add(new)
                created += 1
        db.session.commit()
        logger.info(f"Import terminé: {created} créées, {updated} mises à jour")


def run_structures_scraper():
    with APP.app_context():
        if 'structures' not in scheduler.scrapers:
            logger.error("Scraper 'structures' non trouvé dans scheduler")
            return
        logger.info("Exécution du scraper 'structures'...")
        res = scheduler.executer_maintenant('structures')
        logger.info(f"Résultat: {res}")


if __name__ == '__main__':
    import_sources()
    run_structures_scraper()
