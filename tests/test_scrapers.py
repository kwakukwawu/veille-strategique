import pytest
from bs4 import BeautifulSoup
from backend.scraping.scrapers.pam_scraper import PAMScraper
from backend.scraping.scrapers.fao_scraper import FAOScraper
from backend.scraping.scrapers.pnud_scraper import PNUDScraper

SIMPLE_HTML = '''
<html><head><title>Test</title><meta name="description" content="Desc here"><meta name="author" content="OrgX"></head>
<body><article><h1>Offer Title</h1><p>Some description for the offer.</p><time datetime="2026-01-01T12:00:00Z">1 Jan 2026</time></article></body></html>
'''

class DummyScraper(PAMScraper):
    def __init__(self):
        super().__init__()
    def recuperer_page(self, url):
        return BeautifulSoup(SIMPLE_HTML, 'html.parser')

class DummyFAO(FAOScraper):
    def __init__(self):
        super().__init__()
    def recuperer_page(self, url):
        return BeautifulSoup(SIMPLE_HTML, 'html.parser')

class DummyPNUD(PNUDScraper):
    def __init__(self):
        super().__init__()
    def recuperer_page(self, url):
        return BeautifulSoup(SIMPLE_HTML, 'html.parser')

@pytest.mark.parametrize('ScraperClass', [DummyScraper, DummyFAO, DummyPNUD])
def test_parse_offer_page(ScraperClass):
    s = ScraperClass()
    details = s._parse_offer_page('http://example.com')
    assert details is not None
    assert 'Offer Title' in details['titre']
    assert 'Desc here' in details['description'] or 'Some description' in details['description']
    assert details['partenaire'] is not None
    assert details['url'] == 'http://example.com'
