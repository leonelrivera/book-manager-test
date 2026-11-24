"""Pipelines de validación, persistencia en base de datos y recolección para Scrapy.

Valida que cada ítem extraído corresponda efectivamente al libro del catálogo
propio sin inventar campos ausentes, persiste los resultados vinculados mediante
id_libro en la base de datos y mantiene los ítems validados en memoria.
"""

import difflib
import re
import unicodedata
from datetime import datetime
from typing import Any, Optional
from scrapy.exceptions import DropItem

from book_manager.entities.entities import PrecioCompetidor
from book_manager.scraper.items import LibroCompetidorItem


def normalizar_texto(texto: Optional[str]) -> str:
    """Normaliza texto eliminando diacríticos, mayúsculas y signos de puntuación.

    Args:
        texto: Cadena de entrada a normalizar.

    Returns:
        str: Cadena normalizada en minúsculas sin acentos.
    """
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]", " ", sin_tildes.lower()).strip()


class ValidacionLibroPipeline:
    """Pipeline para verificar completitud y correspondencia con el catálogo propio."""

    STOP_WORDS = {
        "de", "la", "el", "los", "las", "un", "una", "en", "para", "y",
        "a", "del", "al", "con", "por", "edicion", "aniversario",
    }

    def process_item(self, item: LibroCompetidorItem, spider: Optional[Any] = None) -> LibroCompetidorItem:
        """Valida que los campos obligatorios existan y correspondan al libro buscado.

        Los campos opcionales ausentes en el sitio web (descripción, formas de pago,
        imagen o autor) se conservan vacíos sin fabricar valores ficticios.

        Args:
            item: Instancia de LibroCompetidorItem extraída por la spider.
            spider: Instancia opcional del Spider en ejecución.

        Returns:
            LibroCompetidorItem: Ítem validado listo para persistencia.

        Raises:
            DropItem: Si el precio es inválido o el ítem no corresponde al libro propio.
        """
        titulo_comp = item.get("titulo_competidor") or ""
        titulo_int = item.get("titulo_interno") or ""
        autor_comp = item.get("autor_competidor") or ""
        autor_int = item.get("autor_interno") or ""

        if not titulo_comp:
            raise DropItem("Ítem descartado: Título de competidor no especificado.")

        precio = item.get("precio")
        if precio is None or precio <= 0:
            raise DropItem(f"Ítem descartado ('{titulo_comp}'): Precio inválido o ausente.")

        t_int_norm = normalizar_texto(titulo_int)
        t_comp_norm = normalizar_texto(titulo_comp)
        palabras_int = [
            p for p in t_int_norm.split()
            if p not in self.STOP_WORDS and (len(p) > 2 or p.isdigit())
        ]
        palabras_comp = [
            p for p in t_comp_norm.split()
            if p not in self.STOP_WORDS and (len(p) > 2 or p.isdigit())
        ]

        if titulo_int and palabras_int:
            coincidencias = sum(
                1 for p in palabras_int
                if re.search(rf"\b{re.escape(p)}\b", t_comp_norm)
            )
            umbral_palabras = max(1, len(palabras_int) // 2)
            if coincidencias < umbral_palabras:
                raise DropItem(
                    f"Ítem descartado: '{titulo_comp}' no coincide con '{titulo_int}'."
                )

        if autor_int:
            a_int_norm = normalizar_texto(autor_int)
            tokens_autor = [p for p in a_int_norm.split() if len(p) > 3]

            if tokens_autor:
                if autor_comp:
                    a_comp_norm = normalizar_texto(autor_comp)
                    coincide_autor = any(
                        bool(re.search(rf"\b{re.escape(tok)}\b", a_comp_norm))
                        for tok in tokens_autor
                    )
                    if not coincide_autor:
                        raise DropItem(
                            f"Ítem descartado: '{titulo_comp}' del autor '{autor_comp}' "
                            f"no coincide con '{autor_int}'."
                        )
                else:
                    desc_norm = normalizar_texto(item.get("descripcion", ""))
                    coincide_en_desc = any(
                        bool(re.search(rf"\b{re.escape(tok)}\b", desc_norm))
                        for tok in tokens_autor
                    )
                    ratio_titulo = difflib.SequenceMatcher(None, t_int_norm, t_comp_norm).ratio()
                    palabras_extra = [
                        p for p in palabras_comp
                        if p not in palabras_int and not p.isdigit()
                    ]
                    if not coincide_en_desc:
                        if len(palabras_int) == 1 and palabras_extra:
                            raise DropItem(
                                f"Ítem descartado: '{titulo_comp}' contiene términos ajenos "
                                f"al título '{titulo_int}' sin confirmación de autor."
                            )
                        if ratio_titulo < 0.78:
                            raise DropItem(
                                f"Ítem descartado: '{titulo_comp}' sin autor confirmado "
                                f"difiere de '{titulo_int}' (ratio={ratio_titulo:.2f})."
                            )

        if not item.get("fecha_extraccion"):
            item["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for campo_opcional in ("descripcion", "formas_pago", "url_imagen", "autor_competidor", "url_libro"):
            if not item.get(campo_opcional):
                item[campo_opcional] = ""

        return item


class PersistenciaDBPipeline:
    """Pipeline encargado de persistir cada ítem validado en la base de datos."""

    def __init__(self) -> None:
        """Inicializa el pipeline sin conexión activa hasta la apertura de la spider."""
        self._repo: Optional[Any] = None

    def open_spider(self, spider: Optional[Any] = None) -> None:
        """Instancia el repositorio de precios de competidor al iniciar el rastreo."""
        from book_manager.database.connection import ConexionDB
        from book_manager.repositories.repositories import RepositorioPrecioCompetidor

        conexion = ConexionDB.get_instancia()
        self._repo = RepositorioPrecioCompetidor(conexion)

    def process_item(self, item: LibroCompetidorItem, spider: Optional[Any] = None) -> LibroCompetidorItem:
        """Persiste el resultado validado en la tabla precios_competidor vinculado a id_libro.

        Args:
            item: Ítem validado con id_libro y precio_web.
            spider: Instancia opcional del Spider en ejecución.

        Returns:
            LibroCompetidorItem: El mismo ítem procesado.
        """
        id_libro = item.get("id_libro")
        precio_web = item.get("precio")
        if self._repo is not None and id_libro and precio_web:
            entidad = PrecioCompetidor(
                id_libro=int(id_libro),
                titulo_competidor=str(item.get("titulo_competidor") or ""),
                autor_competidor=str(item.get("autor_competidor") or ""),
                precio_web=float(precio_web),
                url_imagen=str(item.get("url_imagen") or ""),
                formas_pago=str(item.get("formas_pago") or ""),
                descripcion=str(item.get("descripcion") or ""),
                url_libro=str(item.get("url_libro") or ""),
                fecha_extraccion=item.get("fecha_extraccion"),
            )
            self._repo.crear(entidad)
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
