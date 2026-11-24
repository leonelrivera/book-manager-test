"""Paquete para web scraping de datos de libros de competidores (Cúspide Libros).

Proporciona modelos de ítems, loaders de normalización, pipelines de validación
y persistencia en base de datos, la spider CuspideSpider y utilidades de ejecución.
"""

from book_manager.scraper.items import LibroCompetidorItem
from book_manager.scraper.loaders import LibroCompetidorLoader
from book_manager.scraper.pipelines import (
    AlmacenamientoItemsPipeline,
    PersistenciaDBPipeline,
    ValidacionLibroPipeline,
)
from book_manager.scraper.runner import ejecutar_scraper
from book_manager.scraper.spiders.cuspide_spider import CuspideSpider

__all__ = [
    "AlmacenamientoItemsPipeline",
    "CuspideSpider",
    "LibroCompetidorItem",
    "LibroCompetidorLoader",
    "PersistenciaDBPipeline",
    "ValidacionLibroPipeline",
    "ejecutar_scraper",
]
