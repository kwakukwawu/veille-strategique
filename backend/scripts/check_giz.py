import sys, os
sys.path.insert(0, os.path.abspath('..'))
try:
    from scraping import giz_scraper
    print('giz_scraper file:', getattr(giz_scraper,'__file__', None))
    print('dir:', [n for n in dir(giz_scraper) if 'GIZ' in n or 'giz' in n.lower()][:50])
    print('has GIZScraper:', hasattr(giz_scraper, 'GIZScraper'))
except Exception as e:
    import traceback
    print('ERROR importing giz_scraper')
    traceback.print_exc()