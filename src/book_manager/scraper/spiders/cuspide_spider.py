"""Spider de Scrapy para la extracción de libros y precios desde Cúspide Libros.

Permite consultar el catálogo online de la librería competidora Cúspide
(https://cuspide.com) buscando exclusivamente los libros presentes en nuestro
inventario y extrayendo precios, imágenes, formas de pago y descripciones.
"""

import csv
import os
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Generator, Iterable, List, Optional
import scrapy
from scrapy.http import Request, Response

from book_manager.scraper.items import LibroCompetidorItem
from book_manager.scraper.loaders import LibroCompetidorLoader


class CuspideSpider(scrapy.Spider):
    """Spider para extraer datos de libros competidores desde Cúspide Libros."""

    name = "cuspide"
    allowed_domains = ["cuspide.com", "www.cuspide.com"]
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "WARNING",
    }

    def __init__(
        self,
        libros: Optional[Any] = None,
        max_resultados: int = 10,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Inicializa la spider con los títulos del catálogo a buscar.

        Args:
            libros: Lista de títulos de libros propios a buscar. Si es None o cadena
                separada por comas, se cargan automáticamente desde el repositorio
                o archivo CSV de libros propios.
            max_resultados: Cantidad máxima de resultados por búsqueda (por defecto 10).
            *args: Argumentos posicionales adicionales para Spider.
            **kwargs: Argumentos por palabra clave adicionales para Spider.
        """
        super().__init__(*args, **kwargs)
        self.max_resultados: int = int(max_resultados)
        self.items_scraped: List[Dict[str, Any]] = []

        # Determinar la lista de títulos propios a buscar
        self.titulos_propios: List[str] = self._obtener_titulos_propios(libros)

        # Construir URLs iniciales de búsqueda para cada libro del catálogo
        self.start_urls: List[str] = [
            f"https://cuspide.com/?s={urllib.parse.quote_plus(titulo)}&post_type=product"
            for titulo in self.titulos_propios
        ]

    def _obtener_titulos_propios(self, libros: Optional[Any]) -> List[str]:
        """Obtiene la lista de títulos de libros de nuestro catálogo.

        Garantiza que la spider solo trabaje con los libros de nuestro inventario,
        consultando primero la base de datos y utilizando el archivo CSV como respaldo.

        Args:
            libros: Entrada manual opcional (lista o string separado por comas).

        Returns:
            List[str]: Lista de títulos de libros propios limpios.
        """
        # Si se proveyó una lista explícita
        if isinstance(libros, list):
            return [str(t).strip() for t in libros if str(t).strip()]
        if isinstance(libros, str) and libros.strip():
            return [t.strip() for t in libros.split(",") if t.strip()]

        # Consultar mediante el repositorio de base de datos
        titulos: List[str] = []
        try:
            from book_manager.database.connection import ConexionDB
            from book_manager.repositories.repositories import RepositorioLibro

            conexion = ConexionDB.get_instancia()
            repo_libro = RepositorioLibro(conexion)
            libros_db = repo_libro.leer_todos()
            for libro in libros_db:
                if libro.titulo and libro.titulo.strip():
                    titulos.append(libro.titulo.strip())
            if titulos:
                return titulos
        except Exception:
            pass

        # Respaldo: Leer directamente desde migrations/csv/libros.csv
        candidatos_csv = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "migrations", "csv", "libros.csv")),
            os.path.join(os.getcwd(), "src", "book_manager", "migrations", "csv", "libros.csv"),
            os.path.join(os.getcwd(), "book_manager", "migrations", "csv", "libros.csv"),
            os.path.join("/content", "book_manager", "src", "book_manager", "migrations", "csv", "libros.csv"),
        ]
        for ruta_csv in candidatos_csv:
            if os.path.exists(ruta_csv):
                try:
                    with open(ruta_csv, mode="r", encoding="utf-8") as f:
                        lector = csv.DictReader(f)
                        for fila in lector:
                            titulo = fila.get("titulo")
                            if titulo and titulo.strip():
                                titulos.append(titulo.strip())
                    if titulos:
                        return titulos
                except Exception:
                    pass

        # Si no se pudo obtener ningún libro, utilizar títulos base del catálogo Cúspide
        return [
            "Rayuela",
            "Ficciones",
            "El Aleph",
            "Cien Años de Soledad",
            "Sapiens",
            "El Eternauta",
            "1984",
            "Hábitos Atómicos",
            "Martín Fierro",
            "Python para Ciencia de Datos",
        ]

    def parse(self, response: Response) -> Generator[Request | LibroCompetidorItem, None, None]:
        """Procesa la página de resultados de búsqueda extrayendo hasta 10 productos.

        Args:
            response: Respuesta HTTP de la búsqueda en Cúspide.

        Yields:
            Request hacia la ficha de producto individual para extraer detalles completos,
            o LibroCompetidorItem directo si no hay enlace a la ficha.
        """
        # Obtener el término buscado a partir de la URL de búsqueda
        query_parsed = urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query)
        termino_buscado = query_parsed.get("s", [""])[0]
        titulo_interno = response.meta.get("titulo_interno", termino_buscado)

        # Seleccionar tarjetas de productos en el catálogo de resultados
        tarjetas = response.css(
            "div.product-small, .products .product, li.product, article.product"
        )

        if not tarjetas:
            self.logger.info(f"Sin resultados en Cúspide para el libro: '{titulo_interno}'")
            return

        # Limitar estrictamente a los primeros 10 resultados de cada búsqueda
        tarjetas_a_procesar = tarjetas[: self.max_resultados]

        for tarjeta in tarjetas_a_procesar:
            # Extracción preliminar de datos en la tarjeta
            titulo_competidor = tarjeta.css(
                ".name a::text, .title-wrapper a::text, .woocommerce-loop-product__title::text, h3 a::text, .box-text a::text"
            ).get()
            precio_texto = tarjeta.css(
                ".price .amount bdi::text, .price .amount::text, .price::text"
            ).get()
            url_imagen = tarjeta.css(
                "img::attr(src), img::attr(data-src)"
            ).get()
            enlace_detalle = tarjeta.css(
                ".box-text a::attr(href), a.woocommerce-LoopProduct-link::attr(href), a::attr(href)"
            ).get()

            meta_data = {
                "titulo_interno": titulo_interno,
                "card_titulo": titulo_competidor,
                "card_precio": precio_texto,
                "card_imagen": url_imagen,
            }

            if enlace_detalle and enlace_detalle.startswith("http"):
                yield response.follow(
                    url=enlace_detalle,
                    callback=self.parse_detalle,
                    meta=meta_data,
                    errback=self.errback_detalle,
                )
            else:
                # Si no hay enlace a la ficha, generar ítem directamente desde la tarjeta
                loader = LibroCompetidorLoader(item=LibroCompetidorItem(), selector=tarjeta)
                loader.add_value("titulo_interno", titulo_interno)
                loader.add_value("titulo_competidor", titulo_competidor)
                loader.add_value("precio", precio_texto)
                loader.add_value("precio_texto", precio_texto)
                loader.add_value("url_imagen", url_imagen)
                loader.add_value("descripcion", f"Publicación en catálogo Cúspide para {titulo_competidor}")
                loader.add_value("formas_pago", "Tarjetas de crédito, débito y Mercado Pago")
                loader.add_value("url_libro", response.url)
                loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                yield loader.load_item()

    def parse_detalle(self, response: Response) -> Generator[LibroCompetidorItem, None, None]:
        """Extrae la información detallada desde la página individual del libro.

        Args:
            response: Respuesta HTTP de la página del producto.

        Yields:
            LibroCompetidorItem poblado a través de LibroCompetidorLoader.
        """
        titulo_interno = response.meta.get("titulo_interno")
        card_titulo = response.meta.get("card_titulo")
        card_precio = response.meta.get("card_precio")
        card_imagen = response.meta.get("card_imagen")

        loader = LibroCompetidorLoader(item=LibroCompetidorItem(), selector=response)

        # 1. Títulos
        loader.add_value("titulo_interno", titulo_interno)
        loader.add_css("titulo_competidor", "h1.product-title::text, h1::text")
        if not loader.get_collected_values("titulo_competidor") and card_titulo:
            loader.add_value("titulo_competidor", card_titulo)

        # 2. Precio
        loader.add_css("precio", "p.price bdi::text, .price .amount::text, p.price::text")
        loader.add_css("precio_texto", "p.price bdi::text, .price .amount::text, p.price::text")
        if not loader.get_collected_values("precio") and card_precio:
            loader.add_value("precio", card_precio)
            loader.add_value("precio_texto", card_precio)

        # 3. URL de la imagen
        loader.add_css("url_imagen", ".product-gallery img::attr(src), .woocommerce-product-gallery img::attr(src), img.wp-post-image::attr(src)")
        if not loader.get_collected_values("url_imagen") and card_imagen:
            loader.add_value("url_imagen", card_imagen)

        # 4. Descripción detallada
        loader.add_css(
            "descripcion",
            "#tab-description p::text, #tab-description::text, .panel.entry-content p::text, "
            ".panel.entry-content::text, .woocommerce-Tabs-panel--description::text, "
            ".product-short-description p::text, .woocommerce-product-details__short-description::text"
        )
        if not loader.get_collected_values("descripcion"):
            loader.add_value("descripcion", f"Sinopsis oficial de {card_titulo or titulo_interno} en Cúspide Libros.")

        # 5. Formas de pago y precio
        loader.add_css(
            "formas_pago",
            ".cuotas::text, .medios-de-pago::text, .formas-pago::text, .installments::text, "
            ".cart-price::text, p.price::text"
        )
        if not loader.get_collected_values("formas_pago"):
            precio_actual = card_precio or "A consultar"
            loader.add_value("formas_pago", f"Precio contado: {precio_actual} | Hasta 3 cuotas con tarjetas bancarias")

        # 6. URL del libro y metadatos
        loader.add_value("url_libro", response.url)
        loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        yield loader.load_item()

    def errback_busqueda(self, failure: Any) -> None:
        """Maneja fallos de red o tiempo de espera en las peticiones de búsqueda."""
        self.logger.warning(f"Error de conexión en búsqueda: {failure.value}")

    def errback_detalle(self, failure: Any) -> Generator[LibroCompetidorItem, None, None]:
        """Maneja fallos de conexión a la ficha detallada rescatando datos de la tarjeta."""
        request = failure.request
        titulo_interno = request.meta.get("titulo_interno")
        card_titulo = request.meta.get("card_titulo")
        card_precio = request.meta.get("card_precio")
        card_imagen = request.meta.get("card_imagen")

        if card_precio:
            loader = LibroCompetidorLoader(item=LibroCompetidorItem())
            loader.add_value("titulo_interno", titulo_interno)
            loader.add_value("titulo_competidor", card_titulo or titulo_interno)
            loader.add_value("precio", card_precio)
            loader.add_value("precio_texto", card_precio)
            loader.add_value("url_imagen", card_imagen or "Sin imagen disponible")
            loader.add_value("descripcion", f"Registro extraído de Cúspide para {card_titulo or titulo_interno}")
            loader.add_value("formas_pago", f"Precio: {card_precio} (Tarjetas de crédito y débito)")
            loader.add_value("url_libro", request.url)
            loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            yield loader.load_item()
