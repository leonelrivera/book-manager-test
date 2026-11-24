"""Configuración del framework Scrapy para Book Manager.

Establece las directivas de ejecución, identificación propia del bot,
respeto por robots.txt, políticas de descarga y pipelines activos.
"""

import os
import sys

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

BOT_NAME = "book_manager_scraper"

SPIDER_MODULES = ["book_manager.scraper.spiders"]
NEWSPIDER_MODULE = "book_manager.scraper.spiders"

ROBOTSTXT_OBEY = True

USER_AGENT = (
    "BookManagerBot/1.0 "
    "(+https://github.com/leonelrivera/book-manager-test; proyecto academico)"
)

CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1.0
COOKIES_ENABLED = False

LOG_LEVEL = "WARNING"
FEED_EXPORT_ENCODING = "utf-8"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

ITEM_PIPELINES = {
    "book_manager.scraper.pipelines.ValidacionLibroPipeline": 300,
    "book_manager.scraper.pipelines.PersistenciaDBPipeline": 350,
    "book_manager.scraper.pipelines.AlmacenamientoItemsPipeline": 400,
}
