"""
Init pour le package scrapers
Exporte les scrapers pour faciliter l'import
"""

from .base_scraper import BaseScraper
from .un_scraper import UNScraper
from .educarriere_scraper import EduCarriereScraper
from .pam_scraper import PAMScraper
from .fao_scraper import FAOScraper
from .ue_scraper import UEScraper
from .afd_scraper import AFDScraper
from .pnud_scraper import PNUDScraper
from .worldbank_scraper import WorldBankScraper
from .bad_scraper import BADScraper
from .enabel_scraper import EnabelScraper
from .firca_scraper import FIRCAScraper
from .anader_scraper import AnaderScraper
from .minader_scraper import MinaderScraper
from .dgmp_scraper import DGMPScraper
from .structure_links_scraper import StructuresLinksScraper

__all__ = [
    'BaseScraper','UNScraper','EduCarriereScraper',
    'PAMScraper','FAOScraper','UEScraper','AFDScraper','PNUDScraper',
    'WorldBankScraper','BADScraper','EnabelScraper','FIRCAScraper','AnaderScraper','MinaderScraper','DGMPScraper'
    ,'StructuresLinksScraper'
]
