#!/usr/bin/env python
"""Script de test pour exécuter un scraper et afficher le résultat (dev only).
Usage: python scripts/run_scraper.py pam
"""
import sys
sys.path.insert(0, 'backend')
from app import create_app
from scraping.scheduler import scheduler

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: run_scraper.py <scraper_key>')
        sys.exit(1)
    key = sys.argv[1]
    app = create_app()
    with app.app_context():
        res = scheduler.executer_maintenant(key)
        print('Result:', res)
