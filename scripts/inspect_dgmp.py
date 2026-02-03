import requests
from bs4 import BeautifulSoup

url = 'https://admin.sigomap.gouv.ci'
print('Fetching', url)
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    s = BeautifulSoup(r.content, 'html.parser')
    print('Status:', r.status_code)
    h1 = s.find('h1')
    print('H1:', h1.get_text(strip=True) if h1 else 'None')
    print('\nFirst 20 anchors:')
    for a in s.find_all('a', href=True)[:20]:
        print('-', a.get_text(strip=True)[:60].replace('\n', ' '), '->', a['href'])
    # print first few divs
    print('\nFirst 10 div classes:')
    for d in s.find_all('div')[:10]:
        cls = ' '.join(d.get('class') or [])
        txt = d.get_text(strip=True)[:80]
        print('-', cls or '(no-class)', '->', txt)
except Exception as e:
    print('Error fetching:', e)
