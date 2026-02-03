import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
app = create_app()
with app.app_context():
    loader = app.jinja_loader
    print('searchpath:', getattr(loader, 'searchpath', None))
    print('templates:')
    for t in app.jinja_env.list_templates():
        print(' -', t)
