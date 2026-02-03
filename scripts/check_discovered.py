from backend.config import Config

print('STRUCTURES count:', len(getattr(Config,'STRUCTURES_SCRAPING_TARGETS',[])))
for t in Config.STRUCTURES_SCRAPING_TARGETS[:12]:
    print(t.get('structure'), '->', len(t.get('urls_a_scraper', [])))
