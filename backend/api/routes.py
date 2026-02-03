"""
Routes API principales
Endpoints pour accéder aux offres, mots-clés, et gérer le scraping
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from datetime import datetime
import threading
from urllib.parse import urlparse
import hashlib

from database.models import db, Offre, MotsCles, Source, LogScraping
from database.database import get_default_sources_data
from scraping.keyword_manager import KeywordManager
from scraping.scheduler import scheduler
from scraping.scrapers.structure_links_scraper import StructuresLinksScraper
from scraping.ai_filter_local import LocalAIFilter
from api.middleware import require_auth, require_admin, log_request

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

_SCRAPE_ALL_JOB = {
    'running': False,
    'started_at': None,
    'finished_at': None,
    'result': None,
    'error': None,
}


def _run_all_scrapers():
    """Exécuter tous les scrapers et retourner un dict (sans dépendre du contexte request)."""
    results = []
    sources = Source.query.filter_by(actif=True).all()

    for s in sources:
        try:
            r = scheduler.executer_source(s.id)
            results.append(r)
        except Exception as e:
            results.append({
                'source_id': s.id,
                'source_nom': s.nom,
                'type_scraper': s.type_scraper,
                'statut': 'erreur',
                'message': str(e),
            })

    return {
        'message': 'Scraping global exécuté',
        'total': len(results),
        'results': results
    }

# ==================== OFFRES ====================

@api_bp.route('/offres', methods=['GET'])
@log_request
def lister_offres():
    """
    Lister toutes les offres avec filtrage et pagination
    
    Paramètres query:
    - page: numéro de page (défaut: 1)
    - par_page: offres par page (défaut: 20)
    - source: filtrer par source
    - partenaire: filtrer par partenaire
    - type_offre: filtrer par type
    - mot_cle: filtrer par mot-clé
    """
    page = request.args.get('page', 1, type=int)
    par_page = request.args.get('par_page', 20, type=int)
    source = request.args.get('source')
    partenaire = request.args.get('partenaire')
    type_offre = request.args.get('type_offre')
    mot_cle = request.args.get('mot_cle')
    include_expired = request.args.get('include_expired', '0') in ('1', 'true', 'True')
    
    # Construire la requête
    query = Offre.query.filter_by(actif=True)

    if not include_expired:
        now = datetime.utcnow()
        query = query.filter(
            (Offre.date_cloturation >= now)
        )
    
    if source:
        query = query.filter_by(source=source)
    if partenaire:
        query = query.filter_by(partenaire=partenaire)
    if type_offre:
        query = query.filter_by(type_offre=type_offre)
    if mot_cle:
        query = query.filter(Offre.mots_cles.contains(mot_cle))
    
    # Paginer
    paginate = query.order_by(Offre.date_scrape.desc()).paginate(
        page=page,
        per_page=par_page,
        error_out=False
    )
    
    return jsonify({
        'page': page,
        'par_page': par_page,
        'total': paginate.total,
        'pages': paginate.pages,
        'offres': [o.to_dict() for o in paginate.items]
    }), 200

@api_bp.route('/offres/<int:offre_id>', methods=['GET'])
def obtenir_offre(offre_id):
    """Récupérer une offre spécifique"""
    offre = Offre.query.get_or_404(offre_id)
    return jsonify({'offre': offre.to_dict()}), 200

@api_bp.route('/offres/rechercher', methods=['GET'])
def rechercher_offres():
    """
    Recherche avancée avec texte complet
    
    Paramètres:
    - q: texte à rechercher
    - page: numéro de page
    """
    q = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    par_page = request.args.get('par_page', 20, type=int)
    include_expired = request.args.get('include_expired', '0') in ('1', 'true', 'True')
    
    if not q or len(q) < 2:
        return {'erreur': 'Minimum 2 caractères requis'}, 400
    
    query_text = f"%{q}%"
    query = Offre.query.filter(Offre.actif == True)
    if not include_expired:
        now = datetime.utcnow()
        query = query.filter(
            (Offre.date_cloturation >= now)
        )

    resultats = query.filter(
        (Offre.titre.ilike(query_text)) |
        (Offre.description.ilike(query_text)) |
        (Offre.mots_cles.ilike(query_text))
    ).order_by(Offre.date_scrape.desc()).paginate(page=page, per_page=par_page, error_out=False)
    
    return jsonify({
        'query': q,
        'page': page,
        'par_page': par_page,
        'total': resultats.total,
        'pages': resultats.pages,
        'offres': [o.to_dict() for o in resultats.items]
    }), 200

@api_bp.route('/offres/<int:offre_id>', methods=['DELETE'])
@require_admin
def supprimer_offre(offre_id):
    """Supprimer une offre (soft delete)"""
    offre = Offre.query.get_or_404(offre_id)
    offre.actif = False
    db.session.commit()
    return {'message': 'Offre supprimée'}, 200

# ==================== MOTS-CLÉS ====================

@api_bp.route('/mots-cles', methods=['GET'])
def lister_mots_cles():
    """Lister tous les mots-clés avec pagination"""
    page = request.args.get('page', 1, type=int)
    categorie = request.args.get('categorie')
    
    query = MotsCles.query
    if categorie:
        query = query.filter_by(categorie=categorie)
    
    resultats = query.paginate(page=page, per_page=50)
    
    return jsonify({
        'total': resultats.total,
        'mots_cles': [m.to_dict() for m in resultats.items],
        'categories': KeywordManager.obtenir_categories()
    }), 200

@api_bp.route('/mots-cles', methods=['POST'])
@require_admin
def ajouter_mot_cle():
    """Ajouter un nouveau mot-clé"""
    data = request.get_json()
    
    if not data or not data.get('mot'):
        return {'erreur': 'Mot requis'}, 400
    
    succes = KeywordManager.ajouter_mot_cle(
        data['mot'],
        data.get('categorie', 'Général')
    )
    
    if succes:
        logger.info(f"Mot-clé ajouté: {data['mot']}")
        return {'message': 'Mot-clé ajouté'}, 201
    else:
        return {'erreur': 'Mot-clé déjà existant'}, 409


@api_bp.route('/mots-cles/import', methods=['POST'])
@require_admin
def importer_mots_cles():
    """Importer en masse des mots-clés.

    Body JSON:
    - categorie: string (optionnel)
    - texte: string (optionnel, multi-lignes)
    - mots: list[string] (optionnel)
    """
    data = request.get_json(silent=True) or {}
    categorie = (data.get('categorie') or 'Général').strip() or 'Général'
    texte = data.get('texte')
    mots = data.get('mots')

    items = []
    if isinstance(mots, list):
        items.extend([str(x) for x in mots if x is not None])
    if isinstance(texte, str):
        # split lines, also split on ';'
        for line in texte.splitlines():
            if not line.strip():
                continue
            parts = [p for p in line.split(';') if p is not None]
            items.extend(parts)

    if not items:
        return {'erreur': 'Aucun mot-clé fourni (texte ou mots)'}, 400

    created = 0
    reactivated = 0
    skipped = 0

    for raw in items:
        mot_n = KeywordManager.normaliser_mot(raw)
        if not mot_n:
            skipped += 1
            continue

        existing = MotsCles.query.filter_by(mot=mot_n).first()
        if existing:
            changed = False
            if existing.actif is not True:
                existing.actif = True
                reactivated += 1
                changed = True
            if categorie and (existing.categorie or '') != categorie:
                existing.categorie = categorie
                changed = True
            if changed:
                continue
            skipped += 1
            continue

        db.session.add(MotsCles(mot=mot_n, categorie=categorie, actif=True))
        created += 1

    db.session.commit()
    return jsonify({
        'message': 'Import mots-clés terminé',
        'categorie': categorie,
        'created': created,
        'reactivated': reactivated,
        'skipped': skipped,
        'total_input': len(items)
    }), 200

@api_bp.route('/mots-cles/<int:mot_id>', methods=['DELETE'])
@require_admin
def supprimer_mot_cle(mot_id):
    """Supprimer un mot-clé"""
    succes = KeywordManager.supprimer_mot_cle(mot_id)
    
    if succes:
        return {'message': 'Mot-clé supprimé'}, 200
    else:
        return {'erreur': 'Mot-clé non trouvé'}, 404

# ==================== SOURCES ====================

@api_bp.route('/sources', methods=['GET'])
def lister_sources():
    """Lister les sources de scraping"""
    sources = Source.query.all()
    return jsonify({
        'total': len(sources),
        'sources': [s.to_dict() for s in sources]
    }), 200


@api_bp.route('/sources/sync-default', methods=['POST'])
@require_admin
def sync_sources_default():
    """Synchroniser/ajouter les sources par défaut dans une base déjà initialisée."""
    created = 0
    updated = 0
    activated = 0

    for nom, url_base, type_scraper in (get_default_sources_data() or []):
        s = Source.query.filter_by(nom=nom).first()
        if not s:
            s = Source(nom=nom, url_base=url_base, type_scraper=type_scraper, actif=True)
            db.session.add(s)
            created += 1
            continue

        # upsert champs
        changed = False
        if (s.url_base or '') != (url_base or ''):
            s.url_base = url_base
            changed = True
        if (s.type_scraper or '') != (type_scraper or ''):
            s.type_scraper = type_scraper
            changed = True
        if s.actif is not True:
            s.actif = True
            activated += 1
            changed = True

        if changed:
            updated += 1

    db.session.commit()
    return jsonify({
        'message': 'Sources synchronisées',
        'created': created,
        'updated': updated,
        'activated': activated,
        'total_default': len(get_default_sources_data() or [])
    }), 200


@api_bp.route('/sources/sync-links', methods=['POST'])
@require_admin
def sync_sources_links():
    """Synchroniser toutes les URLs configurées (acteurs + targets) vers des Sources actives.

    Objectif: que chaque lien à scraper apparaisse dans la table `sources` et soit actif.
    """
    created = 0
    updated = 0
    activated = 0
    ignored = 0

    def _is_http_url(u: str) -> bool:
        if not u:
            return False
        try:
            p = urlparse(u)
            return p.scheme in ('http', 'https') and bool(p.netloc)
        except Exception:
            return False

    def _make_source_name(structure: str, url: str) -> str:
        structure = (structure or '').strip() or 'Source'
        url = (url or '').strip()
        try:
            host = (urlparse(url).netloc or '').lower()
        except Exception:
            host = ''
        digest = hashlib.sha1(url.encode('utf-8')).hexdigest()[:8]
        base = f"{structure} | {host} | {digest}" if host else f"{structure} | {digest}"
        return base[:100]

    urls = []
    acteurs = current_app.config.get('TABLEAU_VEILLE_ACTEURS', []) or []
    for a in acteurs:
        structure = (a or {}).get('structure')
        lien = (a or {}).get('lien')
        if structure and lien:
            urls.append((structure, lien))

    targets = current_app.config.get('STRUCTURES_SCRAPING_TARGETS', []) or []
    for t in targets:
        structure = (t or {}).get('structure') or (t or {}).get('nom')
        for u in ((t or {}).get('urls_a_scraper') or []):
            if structure and u:
                urls.append((structure, u))

    # dédoublonner
    seen = set()
    dedup = []
    for structure, u in urls:
        key = (structure or '', (u or '').strip())
        if key in seen:
            continue
        seen.add(key)
        dedup.append((structure, (u or '').strip()))

    for structure, u in dedup:
        if not _is_http_url(u):
            ignored += 1
            continue

        nom = _make_source_name(structure, u)
        s = Source.query.filter_by(nom=nom).first()
        if not s:
            s = Source(nom=nom, url_base=u, type_scraper='structures', actif=True)
            db.session.add(s)
            created += 1
            continue

        changed = False
        if (s.url_base or '') != (u or ''):
            s.url_base = u
            changed = True
        if (s.type_scraper or '') != 'structures':
            s.type_scraper = 'structures'
            changed = True
        if s.actif is not True:
            s.actif = True
            activated += 1
            changed = True
        if changed:
            updated += 1

    db.session.commit()
    return jsonify({
        'message': 'Sources (liens) synchronisées',
        'created': created,
        'updated': updated,
        'activated': activated,
        'ignored': ignored,
        'total_links': len(dedup)
    }), 200


@api_bp.route('/acteurs-veille', methods=['GET'])
def lister_acteurs_veille():
    """Lister les acteurs institutionnels & liens utiles (tableau de veille stratégique)"""
    acteurs = current_app.config.get('TABLEAU_VEILLE_ACTEURS', [])
    return jsonify({'total': len(acteurs), 'acteurs': acteurs}), 200

# ==================== SCHEDULER ====================

@api_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """Obtenir le statut du scheduler"""
    return jsonify(scheduler.obtenir_status()), 200

@api_bp.route('/scheduler/start', methods=['POST'])
@require_admin
def scheduler_start():
    """Démarrer le scheduler manuellement"""
    try:
        scheduler.demarrer()
        return {'message': 'Scheduler démarré'}, 200
    except Exception as e:
        logger.error(f"Erreur start scheduler: {str(e)}")
        return {'erreur': str(e)}, 500

@api_bp.route('/scheduler/stop', methods=['POST'])
@require_admin
def scheduler_stop():
    """Arrêter le scheduler manuellement"""
    try:
        scheduler.arreter()
        return {'message': 'Scheduler arrêté'}, 200
    except Exception as e:
        logger.error(f"Erreur stop scheduler: {str(e)}")
        return {'erreur': str(e)}, 500

@api_bp.route('/scheduler/executer/<scraper_key>', methods=['POST'])
@require_admin
def executer_scraper(scraper_key):
    """Exécuter un scraper immédiatement et retourner un résumé"""
    if scraper_key not in scheduler.scrapers:
        return {'erreur': 'Scraper inconnu'}, 400
    try:
        result = scheduler.executer_maintenant(scraper_key)
        return {'message': f'Scraper {scraper_key} exécuté', 'result': result}, 200
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
        return {'erreur': str(e)}, 500


@api_bp.route('/scheduler/executer-tous', methods=['POST'])
@require_admin
def executer_tous_scrapers():
    """Exécuter tous les scrapers immédiatement et retourner un résumé"""
    try:
        return _run_all_scrapers(), 200
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution globale: {str(e)}")
        return {'erreur': str(e)}, 500


@api_bp.route('/scheduler/executer-tous/async', methods=['POST'])
@require_admin
def executer_tous_scrapers_async():
    """Lancer le scraping global en tâche de fond et retourner immédiatement un job status."""
    if _SCRAPE_ALL_JOB.get('running'):
        return {
            'message': 'Scraping global déjà en cours',
            'job': _SCRAPE_ALL_JOB,
        }, 200

    _SCRAPE_ALL_JOB['running'] = True
    _SCRAPE_ALL_JOB['started_at'] = datetime.utcnow().isoformat()
    _SCRAPE_ALL_JOB['finished_at'] = None
    _SCRAPE_ALL_JOB['result'] = None
    _SCRAPE_ALL_JOB['error'] = None

    app_obj = current_app._get_current_object()

    def _run():
        try:
            with app_obj.app_context():
                _SCRAPE_ALL_JOB['result'] = _run_all_scrapers()
            _SCRAPE_ALL_JOB['error'] = None
        except Exception as e:
            _SCRAPE_ALL_JOB['result'] = None
            _SCRAPE_ALL_JOB['error'] = str(e)
        finally:
            _SCRAPE_ALL_JOB['running'] = False
            _SCRAPE_ALL_JOB['finished_at'] = datetime.utcnow().isoformat()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {
        'message': 'Scraping global lancé',
        'job': _SCRAPE_ALL_JOB,
    }, 202


@api_bp.route('/scheduler/executer-tous/status', methods=['GET'])
@require_admin
def executer_tous_scrapers_status():
    """Récupérer le statut du job de scraping global (async)."""
    return {'job': _SCRAPE_ALL_JOB}, 200


@api_bp.route('/ai/status', methods=['GET'])
def ai_status():
    """Statut IA locale (Ollama) pour l'interface (sans auth)."""
    ai = LocalAIFilter()
    available = ai.is_available()
    return {
        'enabled': bool(ai.enabled),
        'available': bool(available),
        'model': ai.model,
        'ollama_url': ai.ollama_url,
    }, 200


@api_bp.route('/admin/nettoyer-offres-bruit', methods=['POST'])
@require_admin
def nettoyer_offres_bruit():
    """Désactiver (soft delete) des offres de bruit déjà enregistrées."""
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get('dry_run', False))

    sources = data.get('sources')
    if not isinstance(sources, list) or not sources:
        sources = ['PNUD', 'STRUCTURES']

    patterns = data.get('patterns')
    if not isinstance(patterns, list) or not patterns:
        patterns = [
            '/blog', '/news', '/press', '/story', '/stories', '/article', '/photo', '/video',
            '/climate', '/report', '/publications', '/about', '/contact', '/careers',
            '/jobs', '/media', '/events'
        ]

    q = Offre.query.filter(Offre.actif == True, Offre.source.in_(sources))
    candidates = q.all()

    ids_to_disable = []
    for o in candidates:
        url = (o.url or '').lower()
        title = (o.titre or '').lower()
        desc = (o.description or '').lower()
        hay = f"{url} {title} {desc}"
        if any(p in hay for p in patterns):
            ids_to_disable.append(o.id)

    if dry_run:
        return {
            'dry_run': True,
            'sources': sources,
            'patterns': patterns,
            'candidates': len(candidates),
            'to_disable': len(ids_to_disable),
            'ids': ids_to_disable[:200]
        }, 200

    if ids_to_disable:
        Offre.query.filter(Offre.id.in_(ids_to_disable)).update({'actif': False}, synchronize_session=False)
        db.session.commit()

    return {
        'message': 'Nettoyage terminé',
        'sources': sources,
        'patterns': patterns,
        'candidates': len(candidates),
        'disabled': len(ids_to_disable)
    }, 200


@api_bp.route('/admin/purger-offres-expirees', methods=['POST'])
@require_admin
def purger_offres_expirees_maintenant():
    """Exécuter immédiatement la purge des offres expirées (date_cloturation passée)."""
    try:
        res = scheduler.purger_offres_expirees()
        return {'message': 'Purge exécutée', 'result': res}, 200
    except Exception as e:
        logger.error(f"Erreur purge_offres_expirees (admin): {str(e)}", exc_info=True)
        return {'erreur': str(e)}, 500


@api_bp.route('/admin/nettoyer-offres-non-ci', methods=['POST'])
@require_admin
def nettoyer_offres_non_ci():
    """Désactiver (soft delete) les offres dont le lieu d'exécution ne correspond pas à la Côte d'Ivoire."""
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get('dry_run', False))

    sources = data.get('sources')
    if sources is not None and (not isinstance(sources, list) or any(not isinstance(s, str) for s in sources)):
        return {'erreur': 'Paramètre sources invalide (doit être une liste de strings)'}, 400

    q = Offre.query.filter(Offre.actif == True)
    if sources:
        q = q.filter(Offre.source.in_(sources))

    candidates = q.all()
    ci_checker = StructuresLinksScraper()

    ids_to_disable = []
    for o in candidates:
        url = (o.url or '').strip()
        title = (o.titre or '').strip()
        desc = (o.description or '').strip()
        hay = f"{title} {desc} {url}".strip()

        is_ci = False
        try:
            is_ci = bool(ci_checker._matches_ci_terms(hay) or ci_checker._is_ci_domain(url))
        except Exception:
            is_ci = False

        if not is_ci:
            ids_to_disable.append(o.id)

    if dry_run:
        return {
            'dry_run': True,
            'sources': sources or 'ALL',
            'candidates': len(candidates),
            'to_disable': len(ids_to_disable),
            'ids': ids_to_disable[:200]
        }, 200

    if ids_to_disable:
        Offre.query.filter(Offre.id.in_(ids_to_disable)).update({'actif': False}, synchronize_session=False)
        db.session.commit()

    return {
        'message': 'Nettoyage terminé',
        'sources': sources or 'ALL',
        'candidates': len(candidates),
        'disabled': len(ids_to_disable)
    }, 200

# ==================== LOGS ====================

@api_bp.route('/logs-scraping', methods=['GET'])
def lister_logs():
    """Lister les logs de scraping"""
    page = request.args.get('page', 1, type=int)
    source = request.args.get('source')
    
    query = LogScraping.query
    if source:
        query = query.filter_by(source=source)
    
    logs = query.order_by(LogScraping.date_execution.desc()).paginate(
        page=page, per_page=50
    )
    
    return jsonify({
        'total': logs.total,
        'logs': [l.to_dict() for l in logs.items]
    }), 200

# ==================== STATISTIQUES ====================

@api_bp.route('/stats', methods=['GET'])
def obtenir_stats():
    """Obtenir les statistiques globales"""
    now = datetime.utcnow()
    base_query = Offre.query.filter(
        Offre.actif == True,
        (Offre.date_cloturation >= now)
    )

    total_offres = base_query.count()

    offres_par_source = db.session.query(
        Offre.source,
        db.func.count(Offre.id)
    ).filter(
        Offre.actif == True,
        (Offre.date_cloturation >= now)
    ).group_by(Offre.source).all()

    offres_par_partenaire = db.session.query(
        Offre.partenaire,
        db.func.count(Offre.id)
    ).filter(
        Offre.actif == True,
        (Offre.date_cloturation >= now)
    ).group_by(Offre.partenaire).all()
    
    # Derniers logs
    derniers_logs = LogScraping.query.order_by(
        LogScraping.date_execution.desc()
    ).limit(5).all()

    sources_actives = Source.query.filter(Source.actif == True).count()
    
    return jsonify({
        'total_offres': total_offres,
        'sources_actives': sources_actives,
        'offres_par_source': [
            {'source': s, 'nombre': n} for s, n in offres_par_source
        ],
        'offres_par_partenaire': [
            {'partenaire': p, 'nombre': n} for p, n in offres_par_partenaire
        ],
        'derniers_scraping': [l.to_dict() for l in derniers_logs],
        'date_generation': datetime.utcnow().isoformat()
    }), 200
