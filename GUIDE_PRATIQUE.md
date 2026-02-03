# 📚 GUIDE PRATIQUE - Veille Stratégique Étape par Étape

## Bienvenue! Vous êtes novice? Voici comment fonctionnent les fichiers ensemble.

---

## 🧠 COMPRENDRE L'ARCHITECTURE

### **Le flux global** (Simplifié)

```
1. Les SCRAPERS cherchent les offres sur Internet
   ↓
2. Les offres sont SAUVEGARDÉES en base de données
   ↓
3. L'API expose les offres via HTTP
   ↓
4. L'INTERFACE WEB affiche tout joliment
```

### **Les 3 couches de code**

```
FRONTEND (Ce que l'utilisateur voit)
├── HTML/CSS/JavaScript
└── Affiche les offres, formulaires, etc.

    ↕ (Communication par API)

API (La passerelle)
├── Routes.py = Les endpoints
├── Auth.py = Vérifier qui tu es
└── Middleware.py = Vérifier les permissions

    ↕ (Requêtes SQL)

BACKEND (Le cerveau)
├── Models.py = Structure des données
├── Scrapers = Cherchent les offres
├── Scheduler = Lance les scrapers à l'heure
└── Database = SQLite (stockage)
```

---

## 🚀 DÉMARRER LOCALEMENT (Pas à Pas)

### **Étape 1: Préparer l'environnement**

```powershell
# Ouvrir PowerShell dans le dossier du projet
cd c:\Users\HP\Desktop\veille-strategique

# Créer l'environnement virtuel
python -m venv venv

# L'activer (tu verras (venv) avant le prompt)
.\venv\Scripts\activate
```

### **Étape 2: Installer les paquets**

```powershell
# Aller dans le dossier backend
cd backend

# Installer tout ce qui est dans requirements.txt
pip install -r requirements.txt

# Attendre que tout s'installe... (1-2 minutes)
```

### **Étape 3: Démarrer l'app**

```powershell
# Toujours dans backend/
python app.py
```

Tu devrais voir:
```
✓ Base de données initialisée
✓ Données par défaut chargées
✓ Application Flask créée et configurée
✓ Planificateur de scraping démarré

 * Running on http://localhost:5000
```

✅ **Succès!** Ouvre **http://localhost:5000** dans ton navigateur.

---

## 📂 OÙ FAIRE QUOI?

### **Je veux ajouter une nouvelle SOURCE de scraping**

**Exemple**: Scraper ENABEL (Agence belge)

**Fichiers à créer/modifier**:

1. **Créer** `backend/scraping/scrapers/enabel_scraper.py`

```python
from .base_scraper import BaseScraper

class ENABELScraper(BaseScraper):
    def __init__(self):
        super().__init__('ENABEL')
        self.base_url = 'https://enabel.be/tenders'
    
    def scrape(self, mots_cles=None):
        """Scraper les appels d'ENABEL"""
        offres = []
        
        # Récupérer la page
        soup = self.recuperer_page(self.base_url)
        if not soup:
            return offres
        
        # Chercher les éléments HTML contenant les offres
        articles = soup.find_all('div', class_='tender')
        
        for article in articles:
            titre = self.extraire_texte(article.find('h3'))
            lien = article.find('a', href=True)
            url_offre = lien['href'] if lien else None
            
            if titre and url_offre:
                offre = self.creer_offre(
                    titre=titre,
                    source=self.source_nom,
                    url=url_offre,
                    partenaire='ENABEL',
                    type_offre='Appel d\'offres'
                )
                offres.append(offre)
        
        return self.nettoyer_offres_doublons(offres)
```

2. **Enregistrer** dans `backend/scraping/scrapers/__init__.py`:

```python
from .enabel_scraper import ENABELScraper
__all__ = [..., 'ENABELScraper']
```

3. **Ajouter au Scheduler** dans `backend/scraping/scheduler.py`:

```python
self.scrapers = {
    'giz': GIZScraper(),
    'un': UNScraper(),
    'educarriere': EduCarriereScraper(),
    'enabel': ENABELScraper(),  # ← NOUVEAU
}

# Ajouter le job
self.scheduler.add_job(
    func=self._executer_scraper,
    args=['enabel'],
    trigger=CronTrigger(hour=12, minute=0),
    id='scraper_enabel',
    name='Scraper ENABEL',
    replace_existing=True
)
```

4. **Tester immédiatement** (sans attendre 12h):

```powershell
# Dans Python interactif
from app import create_app
from scraping.scheduler import scheduler

app = create_app()
scheduler.executer_maintenant('enabel')
```

---

### **Je veux ajouter une nouvelle PAGE web**

**Exemple**: Page "À propos"

**Fichiers à créer/modifier**:

1. **Créer** `frontend/templates/apropos.html`:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>À propos - Veille Stratégique</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <div class="header-container">
            <div class="logo">
                <div class="logo-icon">VS</div>
                <span>Veille Stratégique</span>
            </div>
            <nav>
                <a href="/">Accueil</a>
                <a href="/offres">Offres</a>
                <a href="/apropos">À propos</a>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            <h1>À propos de Veille Stratégique</h1>
            <p>Nous sommes une plateforme dédiée...</p>
        </div>
    </main>

    <footer>
        <p>&copy; 2026 Veille Stratégique</p>
    </footer>
</body>
</html>
```

2. **Ajouter la route** dans `backend/api/frontend_routes.py`:

```python
@frontend_bp.route('/apropos')
def apropos():
    return render_template('apropos.html')
```

3. **Rafraîchir le navigateur** - C'est prêt!

---

### **Je veux ajouter un nouvel ENDPOINT API**

**Exemple**: Endpoint pour obtenir les offres "urgentes"

**Fichier à modifier**: `backend/api/routes.py`

```python
@api_bp.route('/offres/urgentes', methods=['GET'])
def offres_urgentes():
    """Obtenir les offres urgentes (qui ferment dans 7 jours)"""
    from datetime import datetime, timedelta
    
    date_limite = datetime.utcnow() + timedelta(days=7)
    
    offres = Offre.query.filter(
        Offre.date_cloturation <= date_limite,
        Offre.actif == True
    ).all()
    
    return jsonify({
        'total': len(offres),
        'offres': [o.to_dict() for o in offres]
    }), 200
```

**Tester dans le navigateur**:
```
http://localhost:5000/api/offres/urgentes
```

---

### **Je veux modifier la BASE DE DONNÉES**

**Exemple**: Ajouter un champ "Budget" aux offres

1. **Modifier le modèle** dans `backend/database/models.py`:

```python
class Offre(db.Model):
    # ... (fields existants)
    budget = db.Column(db.Float)  # ← NOUVEAU
    devise = db.Column(db.String(10), default='USD')  # ← NOUVEAU
```

2. **Créer une migration** (à faire plus tard):

```powershell
# Pour l'instant, la base se recrée automatiquement en dev
# En production, il faudrait:
# alembic revision --autogenerate -m "Ajouter budget aux offres"
# alembic upgrade head
```

3. **Redémarrer l'app**:

```powershell
# Ctrl+C pour arrêter
# Puis relancer:
python app.py
```

---

### **Je veux ajouter un MOT-CLÉ**

**Option 1: Directement en base (via API)**

```powershell
# Dans Python interactif
from app import create_app
from scraping.keyword_manager import KeywordManager

app = create_app()
with app.app_context():
    KeywordManager.ajouter_mot_cle('Énergie renouvelable', 'Chaîne de valeur')
    print("✓ Mot-clé ajouté")
```

**Option 2: Via l'API HTTP**

```bash
curl -X POST http://localhost:5000/api/mots-cles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token-admin@veille.ci" \
  -d '{"mot":"Aquaculture","categorie":"Chaîne de valeur"}'
```

---

### **Je veux changer les COULEURS du logo**

**Fichier**: `frontend/static/css/style.css` (lignes 1-20)

```css
:root {
    --primary-orange: #FF8C00;      /* Change ici */
    --primary-blue: #0066CC;        /* Change ici */
    --dark-black: #1a1a1a;          /* Change ici */
}
```

Les couleurs actuelles:
- **Orange**: `#FF8C00`
- **Bleu**: `#0066CC`
- **Noir**: `#1a1a1a`

Rafraîchis le navigateur, et c'est appliqué partout!

---

## 🔍 COMPRENDRE UN SCRAPER

### **Anatomie d'un Scraper**

```python
class MonScraper(BaseScraper):
    def __init__(self):
        # Initialiser avec le nom de la source
        super().__init__('Mon Source')
        self.base_url = 'https://example.com'
    
    def scrape(self, mots_cles=None):
        # mots_cles = ['Agriculture', 'Cacao', ...]
        
        offres = []
        
        # Récupérer la page HTML
        soup = self.recuperer_page(self.base_url)
        if not soup:
            return offres  # Erreur réseau
        
        # Trouver les éléments
        articles = soup.find_all('div', class_='article')
        
        for article in articles:
            # Extraire les infos
            titre = self.extraire_texte(article.find('h2'))
            lien = article.find('a', href=True)['href']
            
            # Vérifier si contient les mots-clés
            mots_trouves = self.matcher_mots_cles(titre, mots_cles)
            
            # Créer l'offre
            offre = self.creer_offre(
                titre=titre,
                source=self.source_nom,
                url=lien,
                mots_cles_trouves=mots_trouves
            )
            offres.append(offre)
        
        return offres
```

### **Méthodes utiles (de BaseScraper)**

| Méthode | Utilité | Exemple |
|---------|---------|---------|
| `recuperer_page(url)` | Télécharger + parser HTML | `soup = self.recuperer_page('https://...')` |
| `extraire_texte(element)` | Lire le texte d'un élément HTML | `titre = self.extraire_texte(soup.find('h2'))` |
| `matcher_mots_cles(texte, mots)` | Trouver les mots-clés | `mots_trouves = self.matcher_mots_cles(titre, ['Cacao'])` |
| `creer_offre(...)` | Créer un dict standardisé | `offre = self.creer_offre(titre='...', source='...')` |
| `nettoyer_offres_doublons(offres)` | Supprimer les doublons | `offres = self.nettoyer_offres_doublons(offres)` |

---

## 🐛 DÉPANNAGE

### **Problème: "ModuleNotFoundError: No module named 'flask'"**

```powershell
# Tu as oublié d'installer les dépendances!
pip install -r backend/requirements.txt
```

### **Problème: "Address already in use"**

```powershell
# Un autre processus utilise le port 5000
# Soit attendre 2 minutes, soit:

# Trouver le processus
netstat -ano | findstr :5000

# Tuer le processus (remplacer PID)
taskkill /PID 1234 /F
```

### **Problème: Base de données corrompue**

```powershell
# Supprimer la base et la recréer
rm backend\veille_strategique.db

# Relancer app.py
python app.py
```

### **Problème: Les mots-clés ne s'affichent pas**

```powershell
# Vérifier qu'ils sont en base
python

from app import create_app
from database.models import MotsCles

app = create_app()
with app.app_context():
    mots = MotsCles.query.all()
    for m in mots:
        print(m.mot)
```

---

## 📊 VÉRIFIER QUE TOUT FONCTIONNE

```powershell
# 1. Vérifier la base de données
python
>>> from app import create_app
>>> from database.models import Offre, MotsCles
>>> app = create_app()
>>> with app.app_context():
...     print(f"Offres: {Offre.query.count()}")
...     print(f"Mots-clés: {MotsCles.query.count()}")

# 2. Tester un scraper
>>> with app.app_context():
...     from scraping.scrapers import GIZScraper
...     scraper = GIZScraper()
...     offres = scraper.scrape()
...     print(f"Trouvé: {len(offres)} offres")

# 3. Tester l'API
# Ouvre dans le navigateur:
# http://localhost:5000/api/stats
```

---

## 🎯 RÉSUMÉ DES FICHIERS CLÉS

| Fichier | Rôle |
|---------|------|
| `app.py` | Lance tout |
| `config.py` | Paramètres globaux |
| `database/models.py` | Structure des données |
| `database/database.py` | Initialise la BD |
| `scraping/scrapers/` | Cherchent les offres |
| `scraping/scheduler.py` | Lance les scrapers à l'heure |
| `scraping/keyword_manager.py` | Gère les mots-clés |
| `api/routes.py` | Les endpoints HTTP |
| `api/auth.py` | Connexion/auth |
| `api/middleware.py` | Permissions |
| `frontend/templates/` | Pages HTML |
| `frontend/static/css/style.css` | Couleurs & design |
| `frontend/static/js/app.js` | Logique client (fetch, etc.) |

---

## ✅ CHECKLIST - Avant de lancer

- [ ] Python 3.8+ installé
- [ ] Virtual env activé (`venv\Scripts\activate`)
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Tu es dans le dossier `backend/`
- [ ] Pas d'erreur au lancement (`python app.py`)
- [ ] Page d'accueil s'ouvre en `http://localhost:5000`
- [ ] API répond: `http://localhost:5000/api/stats`

---

## 🚀 PROCHAINES ÉTAPES

1. **Tester les scraping**: Ajoute tes propres sources
2. **Personnaliser les mots-clés**: Ajoute ceux spécifiques à ton secteur
3. **Améliorer le design**: Change les couleurs, ajoute un logo
4. **Ajouter des utilisateurs**: Crée des comptes dans la base
5. **Mettre en production**: Deploy sur un serveur (Heroku, PythonAnywhere, etc.)

---

**Besoin d'aide? Regarde les fichiers avec 💭 Commentaires - ils expliquent tout!**

Bonne chance! 🎉
