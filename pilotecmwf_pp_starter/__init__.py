""" Initializations """
import os

from mch_python_commons.audit import logger
from pilotecmwf_pp_starter.config.service_settings import ServiceSettings

CONFIG = ServiceSettings('settings.yaml', os.path.join(os.path.dirname(__file__), 'config'))

# Configure logger
logger.apply_logging_settings(CONFIG.logging)
