"""
Module-wide configuration for Hermes.
"""

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.WARNING)

formatter = logging.Formatter("[%(asctime)s %(levelname)s %(thread)d] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
