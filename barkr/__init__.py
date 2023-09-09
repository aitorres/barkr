"""
Module-wide configuration for Barkr.
"""

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s %(levelname)s %(thread)d] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
