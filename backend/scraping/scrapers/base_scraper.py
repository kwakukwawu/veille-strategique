"""
Classe de base abstraite pour tous les scrapers
Définit le contrat que chaque scraper doit respecter
"""

from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Classe abstraite de base pour tous les scrapers"""
    
    def __init__(self, source_nom, user_agent=None, timeout=30):
        """
        Initialiser le scraper
        
        Args:
            source_nom (str): Nom de la source (ex: 'GIZ', 'ENABEL')
            user_agent (str): User agent personnalisé
            timeout (int): Délai d'attente en secondes
        """
        self.source_nom = source_nom
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.offres_trouvees = []
    
    @abstractmethod
    def scrape(self, mots_cles=None):
        """
        Scraper les données (doit être implémenté par chaque scraper concret)
        
        Args:
            mots_cles (list): Liste des mots-clés à chercher
            
        Returns:
            list: Liste des offres trouvées
        """
        pass
    
    def recuperer_page(self, url):
        """
        Récupérer et parser une page HTML
        
        Args:
            url (str): URL à scraper
            
        Returns:
            BeautifulSoup: Objet parsé ou None en cas d'erreur
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            # record effective base for subsequent URL joins
            self._last_effective_base = url
            return BeautifulSoup(response.content, 'html.parser')
        except Timeout:
            logger.error(f"Timeout lors de l'accès à {url}")
            return None
        except requests.exceptions.SSLError as ssl_err:
            # Tentative de récupération via variante d'hôte (www/without-www)
            logger.warning(f"SSL Error for {url}: {ssl_err}. Trying host variants...")
            try:
                if "//www." in url:
                    alt = url.replace("//www.", "//")
                else:
                    # add www
                    parts = url.split("//", 1)
                    alt = parts[0] + "//www." + parts[1]
                response = self.session.get(alt, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"SSL fallback successful with alternate host {alt}")
                self._last_effective_base = alt
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                logger.warning(f"Alternate host attempt failed for {url}: {e}. Will attempt verify=False as last resort.")
                try:
                    # Last resort: bypass verification but log clearly
                    response = self.session.get(url, timeout=self.timeout, verify=False)
                    response.raise_for_status()
                    logger.warning(f"Insecure SSL fallback used for {url} (verify=False). Ensure this is acceptable.")
                    self._last_effective_base = url
                    return BeautifulSoup(response.content, 'html.parser')
                except Exception as e2:
                    logger.error(f"All SSL fallback attempts failed for {url}: {e2}")
                    return None
        except RequestException as e:
            logger.error(f"Erreur réseau pour {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du parsing de {url}: {str(e)}")
            return None
    
    def extraire_texte(self, element):
        """Extraire le texte brut d'un élément"""
        if element is None:
            return ""
        return element.get_text(strip=True)
    
    def matcher_mots_cles(self, texte, mots_cles):
        """
        Trouver les mots-clés présents dans un texte
        
        Args:
            texte (str): Texte à analyser
            mots_cles (list): Liste des mots-clés
            
        Returns:
            list: Mots-clés trouvés
        """
        if not mots_cles or not texte:
            return []
        
        texte_lower = texte.lower()
        mots_trouves = []
        
        for mot in mots_cles:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
        
        return mots_trouves
    
    def creer_offre(self, titre, source, url, description=None, 
                   date_pub=None, date_clot=None, type_offre=None, 
                   partenaire=None, mots_cles_trouves=None):
        """
        Créer un dictionnaire représentant une offre
        
        Returns:
            dict: Offre structurée
        """
        return {
            'titre': titre,
            'source': source,
            'url': url,
            'description': description or '',
            'date_publication': date_pub,
            'date_cloturation': date_clot,
            'type_offre': type_offre or 'Offre',
            'partenaire': partenaire or self.source_nom,
            'mots_cles': ','.join(mots_cles_trouves) if mots_cles_trouves else '',
        }
    
    def nettoyer_offres_doublons(self, offres):
        """Supprimer les doublons basé sur l'URL"""
        urls_vues = set()
        offres_uniques = []
        
        for offre in offres:
            if offre['url'] not in urls_vues:
                urls_vues.add(offre['url'])
                offres_uniques.append(offre)
        
        return offres_uniques
    
    def logger_execution(self, nombre_offres, nombre_nouvelles, statut='succes', message_erreur=None):
        """Enregistrer l'exécution du scraper"""
        log_data = {
            'source': self.source_nom,
            'nombre_offres': nombre_offres,
            'nombre_nouvelles': nombre_nouvelles,
            'statut': statut,
            'message_erreur': message_erreur,
            'timestamp': datetime.utcnow()
        }
        logger.info(f"[{self.source_nom}] Scraping terminé: {nombre_offres} offres, {nombre_nouvelles} nouvelles")
        return log_data
