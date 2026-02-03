import sys, os
sys.path.insert(0, os.path.abspath('..'))
try:
    import scraping
    print('scraping:', scraping.__file__)
    print('listing:', os.listdir(os.path.dirname(scraping.__file__)))
    from scraping import giz_scraper
    print('giz module file:', getattr(giz_scraper, '__file__', None))
    print('GIZScraper in giz_scraper:', hasattr(giz_scraper, 'GIZScraper'))
except Exception as e:
    print('ERROR', type(e), e)
