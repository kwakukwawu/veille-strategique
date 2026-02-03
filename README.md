# Veille Stratégique - Plateforme de Collecte d'Offres

Plateforme intelligente de **monitoring et collecte d'offres** pour les chaînes de valeur agricoles en Côte d'Ivoire.

## Présentation (démo)

### Pitch (30 secondes)

**Veille Stratégique** centralise automatiquement les offres (appels d’offres, formations, opportunités) issues de plusieurs plateformes et institutions. L’objectif est de gagner du temps, éviter de rater les dates limites, et disposer d’un tableau de bord de suivi.

### Parcours de démo (3–5 minutes)

1. **Accueil**: statistiques + état IA + bouton **Lancer le scraping**
2. **Offres**: liste filtrée (offres actives) + recherche + détail
3. **Détail offre**: résumé + date butoir + lien direct
4. **Scheduler**: statut du planificateur + logs de scraping + exécution manuelle d’un scraper si besoin

### URLs utiles

- Accueil: `http://127.0.0.1:5000/`
- Offres: `http://127.0.0.1:5000/offres`
- Scheduler: `http://127.0.0.1:5000/scheduler`
- Connexion: `http://127.0.0.1:5000/connexion`

### KPIs (définition)

- **Total Offres**: nombre d'offres **actives** avec **date butoir connue et non dépassée** (`actif=True` + `date_cloturation` définie et >= maintenant).
- **Sources actives**: nombre de sources de scraping dont `actif=True` (table `sources`).

## Objectif

Scraper automatiquement et centraliser les offres d'appels (travaux, formations, bourses, etc.) provenant de :
- **GIZ** - Agence allemande de coopération
- **ENABEL** - Agence belge de développement
- **Institutions gouvernementales** - MINADER, ANADER, FIRCA
- **Nations Unies** - FAO, PAM, PNUD, Banque Mondiale
- **EduCarrière** - Plateforme d'emploi et formations

## 📋 Chaînes de Valeur Suivies

- Anacarde, Cacao, Agroforesterie, Agriculture
- Développement rural et entrepreneuriat
- Environnement et changement climatique
- Autonomisation des femmes et emploi des jeunes
- Microfinance et économie circulaire

## 🚀 Démarrage Rapide

### 1. Installation

```bash
# Cloner le projet
git clone <repo-url>
cd veille-strategique

# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install -r backend/requirements.txt
```

### 2. Configuration

```bash
# Créer le fichier .env
cp .env.example backend/.env

# Éditer avec vos paramètres
# DATABASE_URL, SECRET_KEY, CONTACT_EMAIL, etc.
```

### 3. Lancer l'application

```bash
# Du dossier backend
cd backend
python app.py
```

L'application s'ouvre sur `http://localhost:5000`

## ⭐ Fonctionnalités clés

- **Scraping multi-sources** avec logs
- **Filtrage strict SinDev (ultra-strict)**: seules les offres correspondant au périmètre SinDev sont conservées/affichées
- **Date butoir obligatoire**: toute offre sans date butoir exploitable est rejetée
- **Côte d'Ivoire uniquement** (si activé): l'offre doit indiquer une exécution/mission en Côte d'Ivoire
- **Domaines d'intervention SinDev** (si activé): l'offre doit être alignée sur des mots-clés métiers
- **Contexte “appel d'offres / consultance”** (si activé): l'offre doit clairement être un marché/AMI/consultance
- **Extraction PDF (si lien PDF)**: téléchargement contrôlé + extraction texte pour enrichir le filtrage et le résumé
- **Mise à jour des dates**: si une offre est re-scrapée, ses champs (dont date butoir) sont mis à jour
- **IA locale (optionnelle)**: résumé/filtrage via Ollama si disponible
- **Authentification admin persistante** (session conservée côté navigateur)

## Périmètre SinDev (règles de tri)

Le tri est volontairement strict afin de supprimer les offres “bruit” (hors Côte d'Ivoire, hors métiers SinDev, sans date butoir, ou non liées à un processus d'appel d'offres/consultance).

Une offre est **retenue** si elle respecte:

1. **Date butoir connue** et **non expirée**
2. **Côte d'Ivoire** (mots-clés pays + villes/termes géographiques, et détection de “lieu d'exécution/mission” quand présent)
3. **Domaines SinDev** (mots-clés d'intervention)
4. **Contexte “appel d'offres / consultance”** (AMI, AO, RFP/RFQ, consultancy, etc.)

Sinon, elle est enregistrée en base comme `inactif` (ou ignorée selon la source) et n'apparaît pas dans l'UI.

Les paramètres sont centralisés dans `backend/config.py`.

## 📁 Structure du Projet

```
backend/
├── app.py                    # Application Flask principale
├── config.py                 # Configuration centralisée
├── requirements.txt          # Dépendances Python
│
├── api/                      # Couche API
│   ├── routes.py            # Endpoints REST
│   ├── auth.py              # Authentification
│   └── middleware.py        # Middleware (permissions)
│
├── scraping/                # Moteur de scraping
│   ├── scrapers/            # Scrapers par source
│   │   ├── base_scraper.py  # Classe abstraite
│   │   ├── gov_scraper.py   # GIZ, gouvernements
│   │   ├── un_scraper.py    # Nations Unies
│   │   └── educarriere_scraper.py
│   ├── scheduler.py         # Orchestrateur des tâches
│   ├── keyword_manager.py   # Gestion des mots-clés
│   └── giz_scraper.py       # Legacy
│
├── database/                # Couche données
│   ├── models.py            # Modèles SQLAlchemy
│   └── database.py          # Initialisation BD
│
└── migrations/              # Migrations de schéma

frontend/
├── templates/               # Pages HTML
│   ├── index.html          # Accueil
│   ├── offres.html         # Liste des offres
│   ├── connexion.html      # Login
│   └── ...
└── static/
    ├── css/
    │   └── style.css       # Thème (orange/bleu/noir)
    └── js/
        └── app.js          # Client-side logic
```

## 🔌 Endpoints API

### Offres
- `GET /api/offres` - Lister les offres (paginated)
- `GET /api/offres/<id>` - Détail d'une offre
- `GET /api/offres/rechercher?q=<text>` - Recherche texte
- `DELETE /api/offres/<id>` - Supprimer (admin)

### Mots-clés
- `GET /api/mots-cles` - Lister
- `POST /api/mots-cles` - Ajouter (admin)
- `DELETE /api/mots-cles/<id>` - Supprimer (admin)

### Scheduler
- `GET /api/scheduler/status` - Statut des jobs
- `POST /api/scheduler/executer/<scraper>` - Lancer un scraper (admin)

### Statistiques
- `GET /api/stats` - Statistiques globales

### Authentification
- `POST /auth/login` - Se connecter
- `POST /auth/logout` - Se déconnecter
- `GET /auth/profil` - Profil utilisateur

## 🎨 Thème et Couleurs

Le design utilise les couleurs du logo:
- **Orange**: `#FF8C00` - Actions principales, badges
- **Bleu**: `#0066CC` - Liens, éléments secondaires
- **Noir**: `#1a1a1a` - Texte principal, headers

Fichier CSS: `frontend/static/css/style.css`

## 👤 Authentification

**Compte démo** (à remplacer en production):
- Email: `admin@veille.ci`
- Password: `admin123`

Rôles:
- `admin` - Accès complet
- `lecteur` - Lecture seule
- `editeur` - Lecture + modification offres

## 🧯 Dépannage rapide (jour de démo)

- **Le scraping ne se lance pas**: vérifier la connexion admin (navbar: Déconnexion) et la page `/scheduler` (logs).
- **Je vois 0 offre**: cela signifie en général que le tri strict a rejeté les offres candidates (souvent: date butoir manquante/non parsée, ou offre hors périmètre SinDev). Vérifier les logs du backend (lignes `[FILTER] REJECT ... reasons=...`).
- **Les offres expirées apparaissent**: lancer une purge manuelle (si disponible) ou attendre la purge horaire; vérifier que la date butoir est correctement parsée.
- **L’IA n’apparaît pas**: vérifier qu’Ollama tourne (port `11434`) ou désactiver l’IA (mode fallback).
- **Le site ne se met pas à jour**: faire `Ctrl+F5` (cache navigateur).

## ⚙️ Configuration Scheduler

Les scraping s'exécutent automatiquement:

- **Scraping global**: toutes les **1h**
- **Purge offres expirées**: toutes les **1h** (désactive automatiquement les offres dont la date butoir est passée)

Configurable dans `backend/scraping/scheduler.py`

## 🧠 IA locale (optionnel)

Si Ollama est installé et en cours d’exécution, l’application peut utiliser une IA locale pour filtrer/résumer les offres.

- Service: `http://127.0.0.1:11434`
- Exemple modèle: `llama3.1:8b`
- Statut: `GET /api/ai/status`

## PDF (extraction pour filtrage et résumé)

Si une offre contient un lien PDF (direct ou détecté dans la page), le backend peut:

- Télécharger le PDF avec des limites de sécurité (taille/timeout)
- Extraire le texte (librairie `pypdf`)
- Enrichir la description utilisée par le filtrage strict et/ou l'IA

## 📊 Base de Données

SQLite en développement, migrations avec SQLAlchemy.

Tables principales:
- `offres` - Offres scrappées
- `mots_cles` - Termes de recherche
- `sources` - Sources de scraping
- `utilisateurs` - Comptes admin
- `logs_scraping` - Historique des scraping

## 🔧 Ajouter une Nouvelle Source

1. Créer `backend/scraping/scrapers/nouvlle_source_scraper.py`
2. Hériter de `BaseScraper`
3. Implémenter `scrape(self, mots_cles)`
4. Enregistrer dans `scheduler.py`

Exemple:
```python
from .base_scraper import BaseScraper

class NouvelleSourceScraper(BaseScraper):
    def __init__(self):
        super().__init__('Nouvelle Source')
    
    def scrape(self, mots_cles=None):
        # Votre logique
        return offres
```

## 📝 Notes pour Développeurs

- **Imports relatifs**: Les chemins sont relatifs à `backend/`
- **Variables d'env**: Chargées par `config.py`
- **Mots-clés**: Toujours lire de `KeywordManager`, ne pas hard-coder
- **Erreurs scraping**: Gérées gracieusement, loggées en détail
- **API responses**: JSON avec schéma standard

## Statut actuel (à date)

- UI opérationnelle: `/`, `/offres`, `/scheduler`
- Filtrage SinDev strict activé (date butoir obligatoire + Côte d'Ivoire + domaines + contexte AO/consultance)
- Extraction PDF backend intégrée pour améliorer le filtrage et la qualité des résumés
- Logs de décisions de filtrage disponibles côté backend (accept/reject + raisons)

## 🐳 Docker (Optionnel)

```bash
docker-compose up -d
```

Voir `backend/docker-compose.yml`

## 📧 Contact & Support

- **Email**: contact@veille-strategique.ci
- **Téléphone**: +225 XX XX XX XX
- **Adresse**: Abidjan, Côte d'Ivoire

---

**Développé avec ❤️ pour les chaînes de valeur agricoles**
