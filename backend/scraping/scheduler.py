"""
Planificateur de tâches de scraping
Orchestre l'exécution des scrapers selon un calendrier défini
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from datetime import datetime, timedelta, timezone
import io
import hashlib
import re
import time
import unicodedata
from dateutil import parser as date_parser
from flask import current_app
from pypdf import PdfReader
from requests.exceptions import RequestException
import requests
from sqlalchemy import or_
from urllib.parse import urlparse

from scraping.ai_filter_local import LocalAIFilter

# GIZScraper est défini dans le module parent scraping.giz_scraper
# Importer de manière paresseuse dans __init__ pour éviter d'éventuels import-cycles
from scraping.scrapers import (
    UNScraper, EduCarriereScraper, PAMScraper, FAOScraper, UEScraper,
    AFDScraper, PNUDScraper, WorldBankScraper, BADScraper, EnabelScraper,
    FIRCAScraper, AnaderScraper, MinaderScraper, DGMPScraper, StructuresLinksScraper
)
from scraping.keyword_manager import KeywordManager
from database.models import db, Offre, LogScraping, Source

logger = logging.getLogger(__name__)

class ScrapingScheduler:
    """Planificateur pour les tâches de scraping"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self._job_last_run = {}
        self._last_links_sync_at = None
        self.ai_filter = LocalAIFilter()
        # Enregistrer les scrapers disponibles (clé = type_scraper)
        # GIZScraper importé paresseusement
        try:
            from scraping.giz_scraper import GIZScraper
            giz_inst = GIZScraper()
        except Exception as e:
            logger.warning(f"Import GIZScraper failed: {e}")
            giz_inst = None

        self.scrapers = {
            'giz': giz_inst,
            'un': UNScraper(),
            'educarriere': EduCarriereScraper(),
            'pam': PAMScraper(),
            'fao': FAOScraper(),
            'ue': UEScraper(),
            'afd': AFDScraper(),
            'pnud': PNUDScraper(),
            'worldbank': WorldBankScraper(),
            'bad': BADScraper(),
            'enabel': EnabelScraper(),
            'firca': FIRCAScraper(),
            'anader': AnaderScraper(),
            'minader': MinaderScraper(),
            'dgmp': DGMPScraper(),
            'structures': StructuresLinksScraper(),
        }
    
    def init_app(self, app):
        """Initialiser le planificateur avec une app Flask"""
        self.app = app
        tz = None
        try:
            tz = app.config.get('SCHEDULER_TIMEZONE')
        except Exception:
            tz = None
        if tz:
            self.scheduler.configure(timezone=tz)
    
    def demarrer(self):
        """Démarrer le planificateur"""
        if self.scheduler.running:
            logger.warning("Le planificateur est déjà en cours d'exécution")
            return
        
        # Ajouter les tâches de scraping
        self._ajouter_taches()

        # Listener pour capturer la dernière exécution (succès/erreur)
        def _on_job_event(event):
            try:
                self._job_last_run[event.job_id] = datetime.utcnow()
            except Exception:
                pass

        try:
            self.scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        except Exception:
            pass
        
        self.scheduler.start()
        logger.info("✓ Planificateur de scraping démarré")
    
    def arreter(self):
        """Arrêter le planificateur"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Planificateur arrêté")
    
    def _ajouter_taches(self):
        """Ajouter toutes les tâches de scraping"""
        # Scraping global toutes les 1h (séquentiel) pour éviter des exécutions concurrentes
        self.scheduler.add_job(
            func=self.executer_toutes_sources_actives_programme,
            trigger=IntervalTrigger(hours=1),
            id='scraping_global_1h',
            name='Scraping global (toutes les 1h)',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=20 * 60,
            next_run_time=datetime.utcnow() + timedelta(seconds=20)
        )

        # Purge horaire: désactiver automatiquement les offres expirées
        self.scheduler.add_job(
            func=self.purger_offres_expirees,
            trigger=IntervalTrigger(hours=1),
            id='purge_offres_expirees_1h',
            name='Purge offres expirées (toutes les 1h)',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=20 * 60,
            next_run_time=datetime.utcnow() + timedelta(minutes=5)
        )

        logger.info("✓ Tâches de scraping configurées")

    def executer_toutes_sources_actives_programme(self):
        """Exécuter toutes les sources actives (tâche planifiée) de manière séquentielle."""
        if not self.app:
            return {'error': 'app_not_initialized'}

        with self.app.app_context():
            # Auto-sync des liens (acteurs + targets) vers la table `sources`.
            # Objectif: que toutes les sources à scraper soient présentes en DB et actives.
            try:
                self._auto_sync_sources_links()
            except Exception:
                pass

            source_ids = [s.id for s in Source.query.filter_by(actif=True).all()]

            results = []
            for sid in source_ids:
                try:
                    r = self.executer_source(sid)
                    results.append(r)
                except Exception as e:
                    results.append({
                        'source_id': sid,
                        'statut': 'erreur',
                        'message': str(e),
                    })

            return {
                'message': 'Scraping global (sources actives) planifié exécuté',
                'total': len(results),
                'results': results,
            }

    def _auto_sync_sources_links(self):
        """Synchroniser automatiquement les liens configurés vers la table `sources`.

        Throttle: au plus une synchro toutes les 6h (en mémoire de process).
        """
        now = datetime.utcnow()
        if self._last_links_sync_at is not None:
            try:
                if (now - self._last_links_sync_at) < timedelta(hours=6):
                    return
            except Exception:
                pass

        cfg = getattr(current_app, 'config', {})

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
        acteurs = cfg.get('TABLEAU_VEILLE_ACTEURS', []) or []
        for a in acteurs:
            structure = (a or {}).get('structure')
            lien = (a or {}).get('lien')
            if structure and lien:
                urls.append((structure, lien))

        targets = cfg.get('STRUCTURES_SCRAPING_TARGETS', []) or []
        for t in targets:
            structure = (t or {}).get('structure') or (t or {}).get('nom')
            for u in ((t or {}).get('urls_a_scraper') or []):
                if structure and u:
                    urls.append((structure, u))

        seen = set()
        dedup = []
        for structure, u in urls:
            key = (structure or '', (u or '').strip())
            if key in seen:
                continue
            seen.add(key)
            dedup.append((structure, (u or '').strip()))

        changed_any = False
        for structure, u in dedup:
            if not _is_http_url(u):
                continue
            nom = _make_source_name(structure, u)
            s = Source.query.filter_by(nom=nom).first()
            if not s:
                s = Source(nom=nom, url_base=u, type_scraper='structures', actif=True)
                db.session.add(s)
                changed_any = True
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
                changed = True
            if changed:
                changed_any = True

        if changed_any:
            db.session.commit()

        self._last_links_sync_at = now

    def executer_source(self, source_id: int):
        """Exécuter le scraping pour une Source (table `sources`)."""
        if not self.app:
            return {'error': 'app_not_initialized'}

        with self.app.app_context():
            source = Source.query.get(source_id)
            if not source:
                return {
                    'source_id': source_id,
                    'statut': 'introuvable',
                    'message': 'Source introuvable',
                }

            start_time = time.time()

            type_key = (source.type_scraper or '').strip().lower()
            url_base = (source.url_base or '').strip()

            scraper = None
            scraper_label = None

            if type_key == 'structures' and url_base:
                # IMPORTANT: ne pas réutiliser l'instance globale "structures" (qui scrape tous les targets Config).
                # Ici on veut scraper uniquement l'URL de la source.
                scraper = StructuresLinksScraper()
                scraper_label = 'structures'
                scraper.targets = [{'structure': source.nom, 'urls_a_scraper': [url_base]}]
            elif type_key and type_key in self.scrapers:
                scraper = self.scrapers.get(type_key)
                scraper_label = type_key
            elif url_base:
                # Fallback: si la source a un lien mais pas de scraper dédié, on tente un scraping générique.
                scraper = StructuresLinksScraper()
                scraper_label = 'structures'
                scraper.targets = [{'structure': source.nom, 'urls_a_scraper': [url_base]}]
            else:
                return {
                    'source_id': source.id,
                    'source_nom': source.nom,
                    'type_scraper': source.type_scraper,
                    'statut': 'ignore',
                    'message': 'Aucun url_base et type_scraper non reconnu',
                }

            if scraper is None:
                return {
                    'source_id': source.id,
                    'source_nom': source.nom,
                    'type_scraper': source.type_scraper,
                    'statut': 'indisponible',
                    'message': f"Scraper indisponible pour type_scraper='{type_key}'",
                }

            # Mots-clés
            mots_cles = KeywordManager.obtenir_tous_mots_cles()

            logger.info(f"[{source.nom}] Scraping en cours... (type={source.type_scraper or ''}, mode={scraper_label})")

            try:
                offres = scraper.scrape(mots_cles)
                nombre_nouvelles = self._sauvegarder_offres(offres)

                source.derniere_execusion = datetime.utcnow()
                db.session.commit()

                temps_execution = time.time() - start_time
                log = LogScraping(
                    source=source.nom,
                    nombre_offres_trouvees=len(offres),
                    nombre_offres_nouvelles=nombre_nouvelles,
                    statut='succes',
                    temps_execution=temps_execution
                )
                db.session.add(log)
                db.session.commit()

                logger.info(
                    f"[{source.nom}] ✓ Succès: {len(offres)} offres, {nombre_nouvelles} nouvelles en {temps_execution:.2f}s"
                )

                return {
                    'source_id': source.id,
                    'source_nom': source.nom,
                    'type_scraper': source.type_scraper,
                    'statut': 'ok',
                    'offres_trouvees': len(offres),
                    'offres_nouvelles': nombre_nouvelles,
                    'temps_execution': round(temps_execution, 2),
                    'mode': scraper_label,
                }
            except Exception as e:
                logger.error(f"[{source.nom}] ✗ Erreur: {str(e)}", exc_info=True)
                log = LogScraping(
                    source=source.nom,
                    statut='erreur',
                    message_erreur=str(e)
                )
                db.session.add(log)
                db.session.commit()
                return {
                    'source_id': source.id,
                    'source_nom': source.nom,
                    'type_scraper': source.type_scraper,
                    'statut': 'erreur',
                    'message': str(e),
                    'mode': scraper_label,
                }

    def purger_offres_expirees(self):
        """Archiver (soft delete) les offres dont la date de clôture est passée."""
        if not self.app:
            return {'error': 'app_not_initialized'}

        with self.app.app_context():
            try:
                now = datetime.utcnow()
                candidates = Offre.query.filter(
                    Offre.actif == True,
                    or_(
                        Offre.date_cloturation.is_(None),
                        Offre.date_cloturation < now
                    )
                ).all()

                ids_to_disable = [o.id for o in candidates]

                if ids_to_disable:
                    Offre.query.filter(Offre.id.in_(ids_to_disable)).update(
                        {'actif': False},
                        synchronize_session=False
                    )
                    db.session.commit()

                disabled = len(ids_to_disable)
                logger.info(f"Purge offres expirées: {disabled} désactivées")

                try:
                    log = LogScraping(
                        source='purge_offres_expirees',
                        nombre_offres_trouvees=disabled,
                        nombre_offres_nouvelles=0,
                        statut='succes',
                        temps_execution=0.0
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

                return {'disabled': disabled, 'removed': 0}
            except Exception as e:
                logger.error(f"Erreur purge_offres_expirees: {str(e)}", exc_info=True)
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return {'error': str(e)}
    
    def _executer_scraper(self, scraper_key):
        """Exécuter un scraper spécifique"""
        with self.app.app_context():
            try:
                start_time = time.time()
                scraper = self.scrapers.get(scraper_key)
                if not scraper:
                    logger.error(f"Scraper {scraper_key} non disponible")
                    return
                
                logger.info(f"[{scraper.source_nom}] Scraping en cours...")
                
                # Obtenir les mots-clés
                mots_cles = KeywordManager.obtenir_tous_mots_cles()
                
                # Exécuter le scraper
                offres = scraper.scrape(mots_cles)
                
                # Sauvegarder les offres
                nombre_nouvelles = self._sauvegarder_offres(offres)
                
                # Mettre à jour la source
                source = Source.query.filter_by(nom=scraper.source_nom).first()
                if source:
                    source.derniere_execusion = datetime.utcnow()
                    db.session.commit()
                
                # Enregistrer le log
                temps_execution = time.time() - start_time
                log = LogScraping(
                    source=scraper.source_nom,
                    nombre_offres_trouvees=len(offres),
                    nombre_offres_nouvelles=nombre_nouvelles,
                    statut='succes',
                    temps_execution=temps_execution
                )
                db.session.add(log)
                db.session.commit()
                
                logger.info(f"[{scraper.source_nom}] ✓ Succès: {len(offres)} offres, {nombre_nouvelles} nouvelles en {temps_execution:.2f}s")
                
            except Exception as e:
                logger.error(f"[{scraper_key}] ✗ Erreur: {str(e)}", exc_info=True)
                
                # Enregistrer l'erreur
                log = LogScraping(
                    source=scraper_key,
                    statut='erreur',
                    message_erreur=str(e)
                )
                db.session.add(log)
                db.session.commit()
    
    def _sauvegarder_offres(self, offres):
        """
        Sauvegarder les offres en base de données
        Retourne le nombre d'offres nouvelles
        """
        nombre_nouvelles = 0

        def _norm_text(s: str) -> str:
            s = (s or '').lower().replace('\u00a0', ' ').strip()
            # Normaliser accents (ex: "côte" -> "cote") pour matcher plus facilement les termes CI.
            try:
                s = ''.join(
                    ch for ch in unicodedata.normalize('NFKD', s)
                    if not unicodedata.combining(ch)
                )
            except Exception:
                pass
            return s

        def _build_text(offre_data: dict) -> str:
            parts = [
                offre_data.get('titre', ''),
                offre_data.get('description', ''),
                offre_data.get('type_offre', ''),
                offre_data.get('partenaire', ''),
                offre_data.get('source', ''),
                offre_data.get('mots_cles', ''),
                offre_data.get('url', ''),
            ]
            return _norm_text(' '.join([p for p in parts if p]))

        def _detect_pdf_url(offre_data: dict) -> str:
            url = (offre_data.get('pdf_url') or '').strip()
            if url:
                return url

            main_url = (offre_data.get('url') or '').strip()
            if main_url.lower().endswith('.pdf'):
                return main_url

            desc = (offre_data.get('description') or '')
            m = re.search(r'(https?://\S+?\.pdf(?:\?\S+)?)', desc, flags=re.IGNORECASE)
            if m:
                return m.group(1)

            return ''

        def _extract_pdf_text(pdf_url: str) -> str:
            if not pdf_url:
                return ''

            cfg = getattr(current_app, 'config', {})
            timeout = int(cfg.get('SINDEV_PDF_TIMEOUT', 15))
            max_bytes = int(cfg.get('SINDEV_PDF_MAX_BYTES', 5 * 1024 * 1024))
            max_chars = int(cfg.get('SINDEV_PDF_MAX_CHARS', 4000))

            try:
                r = requests.get(pdf_url, timeout=timeout, stream=True)
                r.raise_for_status()

                ctype = (r.headers.get('content-type') or '').lower()
                if 'pdf' not in ctype and not pdf_url.lower().endswith('.pdf'):
                    return ''

                buf = io.BytesIO()
                total = 0
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        return ''
                    buf.write(chunk)

                buf.seek(0)
                reader = PdfReader(buf)
                text_parts = []
                for page in reader.pages[:10]:
                    try:
                        t = page.extract_text() or ''
                        if t:
                            text_parts.append(t)
                    except Exception:
                        continue

                text = _norm_text('\n'.join(text_parts))
                if not text:
                    return ''
                return text[:max_chars]
            except RequestException:
                return ''
            except Exception:
                return ''

        def _strict_sindev_filter(offre_data: dict, date_cloturation_dt):
            """Filtrage strict Option A (SinDev): CI + domaines + date butoir."""
            cfg = getattr(current_app, 'config', {})
            reasons = []
            soft_reasons = []

            # 1) Date butoir obligatoire et à jour
            now = datetime.utcnow()
            deadline_required = bool(cfg.get('SINDEV_DEADLINE_REQUIRED', False))
            if date_cloturation_dt is None:
                if deadline_required:
                    reasons.append('missing_deadline')
            elif date_cloturation_dt < now:
                reasons.append('expired_deadline')

            text = _build_text(offre_data)

            # 2) Côte d'Ivoire (si activé)
            if cfg.get('SINDEV_CI_ONLY', False):
                ci_terms = [
                    _norm_text(t)
                    for t in (cfg.get('SINDEV_CI_GEO_TERMS') or cfg.get('SINDEV_CI_TERMS') or [])
                    if t
                ]

                url_l = (offre_data.get('url') or '').lower()
                source_l = _norm_text(offre_data.get('source') or '')

                def _match_ci_term(term: str) -> bool:
                    # Tokens très courts => match en "mot" (évite les faux positifs)
                    if len(term) <= 3 and term.isalnum():
                        return re.search(r'(^|\W)' + re.escape(term) + r'(\W|$)', text) is not None
                    return term in text

                url_suggests_ci = ('.ci' in url_l) or ('cotedivoire' in url_l) or ('cote-divoire' in url_l)
                source_suggests_ci = ('ci' in source_l)
                ci_soft_signals = ['abidjan', 'yamoussoukro', 'bouake', 'san pedro', 'sassandra', 'korhogo', 'man']
                text_suggests_ci = any(s in text for s in ci_soft_signals)
                if ci_terms and (not any(_match_ci_term(t) for t in ci_terms)) and (not url_suggests_ci) and (not source_suggests_ci) and (not text_suggests_ci):
                    reasons.append('not_ci')

            # 3) Domaines Sindev (si activé)
            if cfg.get('SINDEV_FOCUS_ENABLED', False):
                focus_terms = [t.lower() for t in (cfg.get('SINDEV_FOCUS_TERMS') or [])]
                if focus_terms and not any(t in text for t in focus_terms):
                    # Assouplissement: on ne rejette pas uniquement sur l'absence de termes focus.
                    # On tag juste la raison pour analyse (visible dans les logs), mais on laisse passer.
                    soft_reasons.append('not_sindev_domain')

            # 4) Contexte "appel d'offres / consultance" obligatoire (mode ultra-strict)
            if cfg.get('SINDEV_TENDER_CONTEXT_ENABLED', False):
                tender_terms_cfg = [t.lower() for t in (cfg.get('SINDEV_TENDER_TERMS') or [])]
                tender_terms_default = [
                    'appel d offres', "appel d'offres", 'dao', 'ami', 'aoi',
                    'avis', 'avis d appel', "avis d'appel", 'consultation', 'marche', 'marché', 'marches',
                    'soumission', 'soumissionner', 'offre', 'proposition',
                    'tender', 'tender notice', 'bid', 'bidding', 'procurement',
                    'request for proposal', 'rfp', 'request for quotation', 'rfq',
                    'expression of interest', 'eoi',
                ]
                tender_terms = list(dict.fromkeys([t for t in (tender_terms_cfg + tender_terms_default) if t]))
                if tender_terms and not any(t in text for t in tender_terms):
                    reasons.append('not_tender_context')

            keep = len(reasons) == 0
            return keep, reasons + soft_reasons

        def _coerce_datetime(value):
            if value is None or value == '':
                return None
            if isinstance(value, datetime):
                dt = value
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            if isinstance(value, str):
                try:
                    dt = date_parser.parse(value)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    return dt
                except Exception:
                    return None
            return None
        
        for offre_data in offres:
            # Enrichissement automatique via PDF (si disponible) pour améliorer le tri IA/filtrage
            try:
                pdf_url = _detect_pdf_url(offre_data)
                if pdf_url:
                    pdf_text = _extract_pdf_text(pdf_url)
                    if pdf_text:
                        offre_data['description'] = f"CONTENU PDF (extrait): {pdf_text}\n\n" + (offre_data.get('description') or '')
                        offre_data['pdf_url'] = pdf_url
                        offre_data['pdf_texte'] = pdf_text
                        try:
                            logger.info(f"[PDF] extracted url={pdf_url} chars={len(pdf_text)}")
                        except Exception:
                            pass
            except Exception:
                pass

            # Normaliser dates (utilisé aussi pour le filtrage strict)
            date_publication = _coerce_datetime(offre_data.get('date_publication'))
            date_cloturation = _coerce_datetime(offre_data.get('date_cloturation'))

            # Filtrage strict SinDev (avant IA / DB)
            try:
                keep_strict, reasons = _strict_sindev_filter(offre_data, date_cloturation)
            except Exception as e:
                keep_strict, reasons = True, [f'filter_error:{type(e).__name__}']

            accept_tag = 'ACCEPT_SOFT' if ('not_sindev_domain' in (reasons or [])) else 'ACCEPT'

            if not keep_strict:
                try:
                    offre_existante = Offre.query.filter_by(url=offre_data.get('url')).first()
                    if offre_existante:
                        offre_existante.actif = False
                        offre_existante.date_scrape = datetime.utcnow()
                except Exception:
                    pass
                try:
                    logger.info(
                        f"[FILTER] REJECT url={offre_data.get('url','')} reasons={','.join(reasons)} titre={str(offre_data.get('titre',''))[:120]}"
                    )
                except Exception:
                    pass
                continue

            # Filtre IA local optionnel (Ollama). Si indisponible, fallback sur le flux normal.
            try:
                ai_res = self.ai_filter.evaluate(offre_data)
            except Exception:
                ai_res = {'keep': True, 'resume': None}

            if not ai_res.get('keep', True):
                try:
                    offre_existante = Offre.query.filter_by(url=offre_data.get('url')).first()
                    if offre_existante:
                        offre_existante.actif = False
                        offre_existante.date_scrape = datetime.utcnow()
                except Exception:
                    pass
            else:
                # Fallback: garantir un résumé minimal même sans IA
                try:
                    d = (offre_data.get('description') or '').strip()
                    if not d:
                        offre_data['description'] = (offre_data.get('titre') or '').strip()
                    else:
                        d = ' '.join(d.split())
                        if len(d) > 240:
                            offre_data['description'] = d[:240] + '...'
                        else:
                            offre_data['description'] = d
                except Exception:
                    pass
                try:
                    logger.info(
                        f"[FILTER] REJECT_AI url={offre_data.get('url','')} titre={str(offre_data.get('titre',''))[:120]}"
                    )
                except Exception:
                    pass
                continue

            ai_resume = (ai_res.get('resume') or '').strip()
            if ai_resume:
                offre_data['description'] = ai_resume

            # Vérifier si l'offre existe déjà
            offre_existante = Offre.query.filter_by(url=offre_data['url']).first()

            if not offre_existante:
                # Créer une nouvelle offre
                nouvelle_offre = Offre(
                    titre=offre_data['titre'],
                    source=offre_data['source'],
                    url=offre_data['url'],
                    description=offre_data.get('description', ''),
                    type_offre=offre_data.get('type_offre', ''),
                    partenaire=offre_data.get('partenaire', ''),
                    mots_cles=offre_data.get('mots_cles', ''),
                    date_publication=date_publication,
                    date_cloturation=date_cloturation,
                    actif=True,
                )
                db.session.add(nouvelle_offre)
                nombre_nouvelles += 1

                try:
                    logger.info(
                        f"[FILTER] {accept_tag} url={offre_data.get('url','')} reasons={','.join(reasons or [])} titre={str(offre_data.get('titre',''))[:120]}"
                    )
                except Exception:
                    pass
            else:
                # Mettre à jour l'offre existante si on récupère des infos plus fraîches
                offre_existante.actif = True
                offre_existante.date_scrape = datetime.utcnow()

                if offre_data.get('titre'):
                    offre_existante.titre = offre_data['titre']

                if offre_data.get('description'):
                    offre_existante.description = offre_data.get('description', '')

                if offre_data.get('type_offre'):
                    offre_existante.type_offre = offre_data.get('type_offre', offre_existante.type_offre)

                if offre_data.get('partenaire'):
                    offre_existante.partenaire = offre_data.get('partenaire', offre_existante.partenaire)

                if offre_data.get('mots_cles'):
                    offre_existante.mots_cles = offre_data.get('mots_cles', offre_existante.mots_cles)

                try:
                    logger.info(
                        f"[FILTER] {accept_tag} url={offre_data.get('url','')} reasons={','.join(reasons or [])} titre={str(offre_data.get('titre',''))[:120]}"
                    )
                except Exception:
                    pass

                if date_publication is not None:
                    offre_existante.date_publication = date_publication

                if date_cloturation is not None:
                    offre_existante.date_cloturation = date_cloturation
        
        db.session.commit()
        return nombre_nouvelles
    
    def executer_maintenant(self, scraper_key):
        """Exécuter un scraper immédiatement (pour tester). Retourne un dict résumé."""
        return self._executer_scraper(scraper_key)

    def _executer_scraper(self, scraper_key):
        """Exécuter un scraper spécifique"""
        with self.app.app_context():
            try:
                start_time = time.time()
                scraper = self.scrapers.get(scraper_key)
                if not scraper:
                    logger.error(f"Scraper {scraper_key} non disponible")
                    return {'error': 'scraper_unavailable'}

                logger.info(f"[{scraper.source_nom}] Scraping en cours...")

                # Obtenir les mots-clés
                mots_cles = KeywordManager.obtenir_tous_mots_cles()

                # Exécuter le scraper
                offres = scraper.scrape(mots_cles)

                # Sauvegarder les offres
                nombre_nouvelles = self._sauvegarder_offres(offres)

                # Mettre à jour la source
                source = Source.query.filter_by(nom=scraper.source_nom).first()
                if source:
                    source.derniere_execusion = datetime.utcnow()
                    db.session.commit()

                # Enregistrer le log
                temps_execution = time.time() - start_time
                log = LogScraping(
                    source=scraper.source_nom,
                    nombre_offres_trouvees=len(offres),
                    nombre_offres_nouvelles=nombre_nouvelles,
                    statut='succes',
                    temps_execution=temps_execution
                )
                db.session.add(log)
                db.session.commit()

                logger.info(f"[{scraper.source_nom}] ✓ Succès: {len(offres)} offres, {nombre_nouvelles} nouvelles en {temps_execution:.2f}s")

                return {
                    'source': scraper.source_nom,
                    'nombre_offres_trouvees': len(offres),
                    'nombre_nouvelles': nombre_nouvelles,
                    'statut': 'succes',
                    'temps_execution': temps_execution
                }

            except Exception as e:
                logger.error(f"[{scraper_key}] ✗ Erreur: {str(e)}", exc_info=True)

                # Enregistrer l'erreur
                log = LogScraping(
                    source=scraper_key,
                    statut='erreur',
                    message_erreur=str(e)
                )
                db.session.add(log)
                db.session.commit()

                return {
                    'source': scraper_key,
                    'statut': 'erreur',
                    'message': str(e)
                }    
    def obtenir_status(self):
        """Obtenir le statut du planificateur"""
        # Le scheduler peut fonctionner même si l'app n'est pas initialisée
        try:
            tz = str(self.scheduler.timezone)
        except Exception:
            tz = None

        dernier_scraping = None
        derniere_purge = None
        try:
            if self.app:
                with self.app.app_context():
                    last_scrape = LogScraping.query.filter(
                        LogScraping.source != 'purge_offres_expirees'
                    ).order_by(LogScraping.date_execution.desc()).first()
                    if last_scrape and last_scrape.date_execution:
                        dernier_scraping = last_scrape.date_execution.isoformat()

                    last_purge = LogScraping.query.filter(
                        LogScraping.source == 'purge_offres_expirees'
                    ).order_by(LogScraping.date_execution.desc()).first()
                    if last_purge and last_purge.date_execution:
                        derniere_purge = last_purge.date_execution.isoformat()
        except Exception:
            pass

        jobs = []
        for job in self.scheduler.get_jobs():
            last = self._job_last_run.get(job.id)
            jobs.append({
                'id': job.id,
                'nom': job.name,
                'derniere_execution': last.isoformat() if last else None,
                'prochaine_execution': job.next_run_time.isoformat() if job.next_run_time else None
            })

        return {
            'actif': self.scheduler.running,
            'timezone': tz,
            'dernier_scraping': dernier_scraping,
            'derniere_purge': derniere_purge,
            'nombre_jobs': len(jobs),
            'jobs': jobs,
        }

# Instance globale
scheduler = ScrapingScheduler()
