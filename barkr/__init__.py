"""
Module-wide configuration for Barkr.
"""

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s %(levelname)s %(thread)d %(name)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
