"""
Module-wide configuration for Barkr.
"""

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

# Do not stream httpx logs on this stream handler
httpx_logger = logging.getLogger("httpx")
httpx_logger.propagate = False

formatter = logging.Formatter(
    "[%(asctime)s %(levelname)s %(thread)d %(name)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
