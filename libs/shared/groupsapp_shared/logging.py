import logging
import os
import sys


def setup_logging(service_name: str) -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format=f"%(asctime)s %(levelname)s [{service_name}:%(name)s] %(message)s",
    )
