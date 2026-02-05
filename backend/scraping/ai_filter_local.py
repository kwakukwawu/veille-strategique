import json
import os
import requests


class LocalAIFilter:
    def __init__(self):
        enabled_raw = os.getenv('LOCAL_AI_FILTER_ENABLED', '').strip()
        on_render = bool(os.getenv('RENDER') or os.getenv('RENDER_SERVICE_ID') or os.getenv('RENDER_EXTERNAL_URL'))

        # Comportement:
        # - En local/dev: auto-enable par défaut (comme avant)
        # - Sur Render: désactivé par défaut (Ollama n'est généralement pas disponible)
        if enabled_raw in ('1', 'true', 'True', 'yes', 'YES'):
            self.enabled = True
        elif enabled_raw in ('0', 'false', 'False', 'no', 'NO'):
            self.enabled = False
        else:
            self.enabled = (not on_render)
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
        self.timeout = int(os.getenv('OLLAMA_TIMEOUT', '25'))
        self.min_score = int(os.getenv('LOCAL_AI_MIN_SCORE', '60'))

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return r.ok
        except Exception:
            return False

    def _prompt(self, offre: dict) -> str:
        titre = (offre.get('titre') or '').strip()
        url = (offre.get('url') or '').strip()
        description = (offre.get('description') or '').strip()
        source = (offre.get('source') or '').strip()
        partenaire = (offre.get('partenaire') or '').strip()
        date_pub = offre.get('date_publication')
        date_clot = offre.get('date_cloturation')

        return (
            "Tu es un assistant de filtrage d'appels d'offres pour la société SinDev (Stat'Innov Developpement).\n"
            "Objectif: garder uniquement les opportunités pertinentes pour des prestations SinDev, ET dont le lieu d'exécution est en Côte d'Ivoire (n'importe où sur le territoire ivoirien).\n\n"
            "Contexte SinDev (prestations typiques): études/diagnostics, enquêtes, collecte de données, M&E, évaluation, statistique, SIG, télédétection, imagerie satellite, renforcement des capacités, assistance technique.\n\n"
            "Analyse cette offre et réponds STRICTEMENT en JSON valide, sans texte autour, avec ce schéma:\n"
            "{\"keep\": true|false, \"score\": 0-100, \"resume\": \"...\", \"lieu_execution_ci\": true|false, \"raisons\": [\"...\"]}\n\n"
            "Règles:\n"
            "- keep=false si le lieu d'exécution n'est pas en Côte d'Ivoire OU si l'offre n'est pas une prestation type SinDev.\n"
            "- keep=false si la date butoir est absente/inconnue.\n"
            "- keep=false si ce n'est PAS un contexte de consultance/prestation/appel d'offres/AMI/DAO/RFP (ex: news, article, événement).\n"
            "- score mesure la pertinence globale (SinDev + CI).\n"
            "- resume: 1-2 phrases, maximum 220 caractères, en français.\n\n"
            f"TITRE: {titre}\n"
            f"SOURCE: {source}\n"
            f"PARTENAIRE: {partenaire}\n"
            f"DATE_PUBLICATION: {date_pub}\n"
            f"DATE_BUTOIR: {date_clot}\n"
            f"URL: {url}\n"
            f"DESCRIPTION: {description[:2000]}\n"
        )

    def evaluate(self, offre: dict) -> dict:
        """Return dict: {'keep': bool, 'score': int, 'resume': str, 'lieu_execution_ci': bool, 'raisons': list, 'used_ai': bool}."""
        if not self.is_available():
            return {'keep': True, 'score': None, 'resume': None, 'lieu_execution_ci': None, 'raisons': [], 'used_ai': False}

        # Règle dure: sans date butoir, on ne garde pas (sinon trop de bruit).
        # Le filtrage strict côté scheduler applique déjà cette règle, mais ici on la réapplique
        # pour aligner le comportement IA et éviter les faux positifs.
        if offre.get('date_cloturation') in (None, '', 'null', 'None'):
            return {
                'keep': False,
                'score': 0,
                'resume': (offre.get('titre') or '').strip()[:220],
                'lieu_execution_ci': None,
                'raisons': ['date_butoir_inconnue'],
                'used_ai': False
            }

        payload = {
            'model': self.model,
            'prompt': self._prompt(offre),
            'stream': False,
            'options': {
                'temperature': 0.1,
            }
        }

        try:
            r = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=self.timeout)
            if not r.ok:
                return {'keep': True, 'score': None, 'resume': None, 'lieu_execution_ci': None, 'raisons': [], 'used_ai': False}

            data = r.json() if r.headers.get('content-type', '').lower().startswith('application/json') else {}
            raw = (data.get('response') or '').strip()
            if not raw:
                return {'keep': True, 'score': None, 'resume': None, 'lieu_execution_ci': None, 'raisons': [], 'used_ai': False}

            # Ollama sometimes returns extra newlines; try to isolate JSON
            start = raw.find('{')
            end = raw.rfind('}')
            if start == -1 or end == -1 or end <= start:
                return {'keep': True, 'score': None, 'resume': None, 'lieu_execution_ci': None, 'raisons': [], 'used_ai': False}

            obj = json.loads(raw[start:end+1])
            keep = bool(obj.get('keep', False))
            score = obj.get('score', None)
            try:
                score = int(score) if score is not None else None
            except Exception:
                score = None

            lieu_ci = bool(obj.get('lieu_execution_ci', False))
            resume = (obj.get('resume') or '').strip()
            raisons = obj.get('raisons') if isinstance(obj.get('raisons'), list) else []

            if score is not None and score < self.min_score:
                keep = False

            if not lieu_ci:
                keep = False

            return {
                'keep': keep,
                'score': score,
                'resume': resume,
                'lieu_execution_ci': lieu_ci,
                'raisons': raisons,
                'used_ai': True
            }
        except Exception:
            return {'keep': True, 'score': None, 'resume': None, 'lieu_execution_ci': None, 'raisons': [], 'used_ai': False}
