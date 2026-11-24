"""Módulo de cargadores de ítems (ItemLoaders) y procesadores de datos.

Transforma, limpia y normaliza los datos crudos extraídos de las páginas web
antes de asignarlos al ítem estructurado LibroCompetidorItem.
"""

import re
from typing import Any, Optional
from itemloaders import ItemLoader
from itemloaders.processors import Join, MapCompose, TakeFirst

from book_manager.scraper.items import LibroCompetidorItem


def normalizar_entero(valor: Any) -> Optional[int]:
    """Convierte un valor en entero positivo si es válido.

    Args:
        valor: Valor de entrada a convertir.

    Returns:
        Optional[int]: Entero convertido o None si no es válido.
    """
    if valor is None:
        return None
    try:
        entero = int(valor)
        return entero if entero > 0 else None
    except (ValueError, TypeError):
        return None


def limpiar_texto(valor: Optional[str]) -> Optional[str]:
    """Limpia espacios en blanco redundantes y saltos de línea de una cadena.

    Args:
        valor: Texto crudo extraído desde HTML.

    Returns:
        Optional[str]: Cadena normalizada o None si queda vacía.
    """
    if not valor:
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return texto if texto else None


def normalizar_precio(valor: Optional[str]) -> Optional[float]:
    """Extrae y normaliza el valor numérico decimal de un precio en texto.

    Maneja formatos como '$ 34.500,00' o '34500.00' convirtiéndolo a float.

    Args:
        valor: Precio en formato textual o numérico.

    Returns:
        Optional[float]: Valor decimal normalizado o None si no es convertible.
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto_limpio = re.sub(r"[^\d.,]", "", texto)
    if not texto_limpio:
        return None

    if "." in texto_limpio and "," in texto_limpio:
        texto_limpio = texto_limpio.replace(".", "").replace(",", ".")
    elif "," in texto_limpio:
        texto_limpio = texto_limpio.replace(",", ".")
    elif texto_limpio.count(".") > 1:
        partes = texto_limpio.split(".")
        texto_limpio = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(texto_limpio)
    except ValueError:
        return None


class LibroCompetidorLoader(ItemLoader):
    """Cargador especializado para poblar y limpiar instancias de LibroCompetidorItem."""

    default_item_class = LibroCompetidorItem
    default_output_processor = TakeFirst()

    id_libro_in = MapCompose(normalizar_entero)
    titulo_interno_in = MapCompose(limpiar_texto)
    autor_interno_in = MapCompose(limpiar_texto)
    titulo_competidor_in = MapCompose(limpiar_texto)
    autor_competidor_in = MapCompose(limpiar_texto)
    precio_in = MapCompose(normalizar_precio)
    precio_texto_in = MapCompose(limpiar_texto)
    url_imagen_in = MapCompose(limpiar_texto)
    url_libro_in = MapCompose(limpiar_texto)
    fecha_extraccion_in = MapCompose(limpiar_texto)

    descripcion_in = MapCompose(limpiar_texto)
    descripcion_out = Join(" ")

    formas_pago_in = MapCompose(limpiar_texto)
    formas_pago_out = Join(" | ")
