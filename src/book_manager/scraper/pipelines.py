"""Pipelines de procesamiento y validación para los ítems extraídos con Scrapy.

Implementa filtros de integridad, descarte de elementos incompletos,
normalización final y recolección de resultados en memoria.
"""

from datetime import datetime
from typing import Any, List, Optional
from scrapy.exceptions import DropItem

from book_manager.scraper.items import LibroCompetidorItem


class ValidacionLibroPipeline:
    """Pipeline para verificar la completitud y coherencia de los libros extraídos."""

    def process_item(self, item: LibroCompetidorItem, spider: Optional[Any] = None) -> LibroCompetidorItem:
        """Valida que los campos obligatorios existan y tengan valores consistentes.

        Args:
            item: Instancia de LibroCompetidorItem extraída por la spider.
            spider: Instancia opcional del Spider en ejecución.

        Returns:
            LibroCompetidorItem validado y complementado.

        Raises:
            DropItem: Si falta el título o el precio es nulo o menor o igual a cero.
        """
        titulo = item.get("titulo_competidor") or item.get("titulo_interno")
        if not titulo:
            raise DropItem("Ítem descartado: Título no especificado.")

        precio = item.get("precio")
        if precio is None or precio <= 0:
            if not item.get("precio_texto"):
                raise DropItem(f"Ítem descartado ('{titulo}'): Precio inválido o ausente.")

        # Asegurar fecha de extracción si no fue fijada por el loader
        if not item.get("fecha_extraccion"):
            item["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Completar valores por defecto para campos opcionales
        if not item.get("descripcion"):
            item["descripcion"] = "Sin descripción disponible"

        if not item.get("formas_pago"):
            item["formas_pago"] = "Tarjetas de crédito, débito y transferencias bancarias"

        if not item.get("url_imagen"):
            item["url_imagen"] = "Sin imagen disponible"

        return item


class AlmacenamientoItemsPipeline:
    """Pipeline para recolectar los ítems validados en una lista interna de la spider."""

    def open_spider(self, spider: Optional[Any] = None) -> None:
        """Inicializa la lista de resultados recolectados al comenzar el rastreo."""
        if spider is not None and not hasattr(spider, "items_scraped"):
            spider.items_scraped = []

    def process_item(self, item: LibroCompetidorItem, spider: Optional[Any] = None) -> LibroCompetidorItem:
        """Agrega una copia en formato diccionario del ítem a la lista de la spider."""
        if spider is not None and hasattr(spider, "items_scraped"):
            spider.items_scraped.append(dict(item))
        return item
