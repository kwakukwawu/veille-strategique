import requests
from backend.scraping.scrapers.dgmp_scraper import DGMPScraper

class FakeResponse:
    def __init__(self, content=b""):
        self.content = content
        self.status_code = 200
    def raise_for_status(self):
        return None


def test_dgmp_ssl_fallback(monkeypatch):
    scraper = DGMPScraper()

    def fake_get(url, timeout=30, verify=True):
        if "//www." in url:
            raise requests.exceptions.SSLError('Hostname mismatch')
        # alternate host returns a simple page with one matching link
        return FakeResponse(b"<html><body><a href='/offre1'>Appel d'offres important</a></body></html>")

    monkeypatch.setattr(scraper.session, 'get', fake_get)

    offres = scraper.scrape()
    assert isinstance(offres, list)
    assert len(offres) == 1
    # When the www host has SSL issues, the scraper should fallback and record the effective base
    assert offres[0]['url'].startswith('https://admin.sigomap.gouv.ci') or "offre1" in offres[0]['titre']


def test_dgmp_ssl_all_fail(monkeypatch):
    scraper = DGMPScraper()

    def always_ssl_err(url, timeout=30, verify=True):
        raise requests.exceptions.SSLError('Cert error')

    monkeypatch.setattr(scraper.session, 'get', always_ssl_err)

    offres = scraper.scrape()
    assert isinstance(offres, list)
    assert len(offres) == 0
