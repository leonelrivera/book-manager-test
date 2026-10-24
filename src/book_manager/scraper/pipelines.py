"""Pipelines de procesamiento y validación para los ítems extraídos con Scrapy.

Implementa filtros de integridad, descarte de elementos incompletos y
normalización final antes de ser entregados al servicio comparador.
"""

from datetime import datetime
from typing import Any
from scrapy.exceptions import DropItem
from scrapy.spiders import Spider

from book_manager.scraper.items import LibroCompetidorItem


class ValidacionLibroPipeline:
    """Pipeline para verificar la completitud y coherencia de los libros extraídos."""

    def process_item(self, item: LibroCompetidorItem, spider: Spider) -> LibroCompetidorItem:
        """Valida que los campos obligatorios existan y tengan valores consistentes.

        Args:
            item: Instancia de LibroCompetidorItem extraída por la spider.
            spider: Instancia del Spider en ejecución.

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
            # Si el precio numérico falló pero hay texto, intentar rescatar o descartar
            if not item.get("precio_texto"):
                raise DropItem(f"Ítem descartado ('{titulo}'): Precio inválido o ausente.")

        # Asegurar fecha de extracción si no fue fijada por el loader
        if not item.get("fecha_extraccion"):
            item["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Completar valores por defecto para campos opcionales
        if not item.get("descripcion"):
            item["descripcion"] = "Sin descripción disponible"

        if not item.get("formas_pago"):
            item["formas_pago"] = "No especificadas"

        if not item.get("url_imagen"):
            item["url_imagen"] = "Sin imagen disponible"

        return item
