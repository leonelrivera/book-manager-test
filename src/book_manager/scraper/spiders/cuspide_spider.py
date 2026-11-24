"""Spider de Scrapy para la extracción de libros y precios desde Cúspide Libros.

Consulta el catálogo online de Cúspide (https://cuspide.com) buscando
exclusivamente los libros registrados en el inventario propio y extrayendo
precio, imagen de portada, formas de pago, descripción y autor sin inventar
datos ausentes.
"""

import csv
import os
import urllib.parse
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Generator, List, Optional
import scrapy
from scrapy.http import Request, Response

from book_manager.scraper.items import LibroCompetidorItem
from book_manager.scraper.loaders import LibroCompetidorLoader


class CuspideSpider(scrapy.Spider):
    """Spider para extraer datos de libros competidores desde Cúspide Libros."""

    name = "cuspide"
    allowed_domains = ["cuspide.com", "www.cuspide.com"]
    custom_settings = {
        "LOG_LEVEL": "WARNING",
    }

    def __init__(
        self,
        libros: Optional[Any] = None,
        max_resultados: int = 10,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Inicializa la spider con los libros del catálogo propio a buscar.

        Args:
            libros: Lista de títulos o diccionarios con id_libro, título y autor.
                Si es None, se cargan automáticamente desde la base de datos.
            max_resultados: Cantidad máxima de resultados por búsqueda (por defecto 10).
            *args: Argumentos posicionales adicionales para Spider.
            **kwargs: Argumentos por palabra clave adicionales para Spider.
        """
        super().__init__(*args, **kwargs)
        self.max_resultados: int = int(max_resultados)
        self.items_scraped: List[Dict[str, Any]] = []
        self.libros_propios: List[Dict[str, Any]] = self._obtener_libros_propios(libros)
        self.titulos_propios: List[str] = [l["titulo"] for l in self.libros_propios]
        self.start_urls: List[str] = [
            f"https://cuspide.com/?s={urllib.parse.quote_plus(l['titulo'])}&post_type=product"
            for l in self.libros_propios
        ]

    def _obtener_libros_propios(self, libros: Optional[Any]) -> List[Dict[str, Any]]:
        """Obtiene la lista de libros (id_libro, título y autor) de nuestro catálogo.

        Args:
            libros: Entrada manual opcional (lista de diccionarios, lista de títulos
                o cadena separada por comas).

        Returns:
            List[Dict[str, Any]]: Lista de diccionarios con 'id_libro', 'titulo' y 'autor'.
        """
        if isinstance(libros, list) and libros and isinstance(libros[0], dict):
            return [
                {
                    "id_libro": item.get("id_libro") or item.get("id"),
                    "titulo": str(item.get("titulo", "")).strip(),
                    "autor": str(item.get("autor", "")).strip(),
                }
                for item in libros
                if str(item.get("titulo", "")).strip()
            ]

        titulos_filtro: Optional[set] = None
        if isinstance(libros, list):
            titulos_filtro = {str(t).strip().lower() for t in libros if str(t).strip()}
        elif isinstance(libros, str) and libros.strip():
            titulos_filtro = {t.strip().lower() for t in libros.split(",") if t.strip()}

        libros_resultado: List[Dict[str, Any]] = []
        try:
            from book_manager.database.connection import ConexionDB
            from book_manager.repositories.repositories import RepositorioLibro

            conexion = ConexionDB.get_instancia()
            repo_libro = RepositorioLibro(conexion)
            libros_db = repo_libro.leer_todos()
            for libro in libros_db:
                if libro.titulo and libro.titulo.strip():
                    t_limpio = libro.titulo.strip()
                    a_limpio = libro.autor.strip() if getattr(libro, "autor", None) else ""
                    if titulos_filtro is None or t_limpio.lower() in titulos_filtro:
                        libros_resultado.append({
                            "id_libro": libro.id,
                            "titulo": t_limpio,
                            "autor": a_limpio,
                        })
            if libros_resultado:
                return libros_resultado
        except Exception:
            pass

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
                            autor = fila.get("autor", "")
                            id_val = int(fila["id"]) if fila.get("id") and str(fila["id"]).isdigit() else None
                            if titulo and titulo.strip():
                                t_limpio = titulo.strip()
                                a_limpio = autor.strip() if autor else ""
                                if titulos_filtro is None or t_limpio.lower() in titulos_filtro:
                                    libros_resultado.append({
                                        "id_libro": id_val,
                                        "titulo": t_limpio,
                                        "autor": a_limpio,
                                    })
                    if libros_resultado:
                        return libros_resultado
                except Exception:
                    pass

        return libros_resultado

    async def start(self) -> AsyncIterator[Request]:
        """Punto de entrada asíncrono (Scrapy 2.13+) que delega en start_requests."""
        for request in self.start_requests():
            yield request

    def start_requests(self) -> Generator[Request, None, None]:
        """Genera las solicitudes iniciales inyectando id_libro, título y autor en meta."""
        for libro in self.libros_propios:
            id_libro = libro.get("id_libro")
            titulo = libro["titulo"]
            autor = libro.get("autor", "")
            url = f"https://cuspide.com/?s={urllib.parse.quote_plus(titulo)}&post_type=product"
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "id_libro": id_libro,
                    "titulo_interno": titulo,
                    "autor_interno": autor,
                },
                dont_filter=True,
                errback=self.errback_busqueda,
            )

    def parse(self, response: Response) -> Generator[Request | LibroCompetidorItem, None, None]:
        """Procesa la página de resultados de búsqueda extrayendo hasta 10 productos.

        Args:
            response: Respuesta HTTP de la búsqueda en Cúspide.

        Yields:
            Request hacia la ficha individual o LibroCompetidorItem directo si no hay enlace.
        """
        query_parsed = urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query)
        termino_buscado = query_parsed.get("s", [""])[0]
        id_libro = response.meta.get("id_libro")
        titulo_interno = response.meta.get("titulo_interno", termino_buscado)
        autor_interno = response.meta.get("autor_interno", "")

        tarjetas = response.css(
            "div.product-small, .products .product, li.product, article.product"
        )
        if not tarjetas:
            self.logger.info(f"Sin resultados en Cúspide para el libro: '{titulo_interno}'")
            return

        tarjetas_a_procesar = tarjetas[: self.max_resultados]

        for tarjeta in tarjetas_a_procesar:
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
                "id_libro": id_libro,
                "titulo_interno": titulo_interno,
                "autor_interno": autor_interno,
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
                loader = LibroCompetidorLoader(item=LibroCompetidorItem(), selector=tarjeta)
                loader.add_value("id_libro", id_libro)
                loader.add_value("titulo_interno", titulo_interno)
                loader.add_value("autor_interno", autor_interno)
                loader.add_value("titulo_competidor", titulo_competidor)
                loader.add_value("precio", precio_texto)
                loader.add_value("precio_texto", precio_texto)
                loader.add_value("url_imagen", url_imagen)
                loader.add_value("url_libro", response.url)
                loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                yield loader.load_item()

    def parse_detalle(self, response: Response) -> Generator[LibroCompetidorItem, None, None]:
        """Extrae la información real disponible desde la página individual del libro.

        Args:
            response: Respuesta HTTP de la página del producto.

        Yields:
            LibroCompetidorItem poblado únicamente con datos reales extraídos de la web.
        """
        id_libro = response.meta.get("id_libro")
        titulo_interno = response.meta.get("titulo_interno")
        autor_interno = response.meta.get("autor_interno")
        card_titulo = response.meta.get("card_titulo")
        card_precio = response.meta.get("card_precio")
        card_imagen = response.meta.get("card_imagen")

        loader = LibroCompetidorLoader(item=LibroCompetidorItem(), selector=response)

        loader.add_value("id_libro", id_libro)
        loader.add_value("titulo_interno", titulo_interno)
        loader.add_value("autor_interno", autor_interno)
        loader.add_css("titulo_competidor", "h1.product-title::text, h1::text")
        if not loader.get_collected_values("titulo_competidor") and card_titulo:
            loader.add_value("titulo_competidor", card_titulo)

        loader.add_css(
            "autor_competidor",
            "p.livriz-authors::text, .product-summary a[href*='autor']::text, "
            ".product-info a[href*='autor']::text, .author a::text, .author::text, "
            ".product_meta a[href*='autor']::text, .posted_in a[href*='autor']::text",
        )

        loader.add_css("precio", "p.price bdi::text, .price .amount::text, p.price::text")
        loader.add_css("precio_texto", "p.price bdi::text, .price .amount::text, p.price::text")
        if not loader.get_collected_values("precio") and card_precio:
            loader.add_value("precio", card_precio)
            loader.add_value("precio_texto", card_precio)

        loader.add_css(
            "url_imagen",
            ".product-gallery img::attr(src), .woocommerce-product-gallery img::attr(src), img.wp-post-image::attr(src)",
        )
        if not loader.get_collected_values("url_imagen") and card_imagen:
            loader.add_value("url_imagen", card_imagen)

        loader.add_css(
            "descripcion",
            "#tab-description p::text, #tab-description::text, .panel.entry-content p::text, "
            ".panel.entry-content::text, .woocommerce-Tabs-panel--description::text, "
            ".product-short-description p::text, .woocommerce-product-details__short-description::text",
        )

        loader.add_css(
            "formas_pago",
            ".cuotas::text, .medios-de-pago::text, .formas-pago::text, .installments::text, "
            ".cart-price::text",
        )

        loader.add_value("url_libro", response.url)
        loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        yield loader.load_item()

    def errback_busqueda(self, failure: Any) -> None:
        """Registra fallos de red o tiempo de espera en las peticiones de búsqueda."""
        self.logger.warning(f"Error de conexión en búsqueda: {failure.value}")

    def errback_detalle(self, failure: Any) -> Generator[LibroCompetidorItem, None, None]:
        """Rescata únicamente los datos reales de la tarjeta si falla la ficha detallada."""
        request = failure.request
        id_libro = request.meta.get("id_libro")
        titulo_interno = request.meta.get("titulo_interno")
        autor_interno = request.meta.get("autor_interno")
        card_titulo = request.meta.get("card_titulo")
        card_precio = request.meta.get("card_precio")
        card_imagen = request.meta.get("card_imagen")

        if card_precio and card_titulo:
            loader = LibroCompetidorLoader(item=LibroCompetidorItem())
            loader.add_value("id_libro", id_libro)
            loader.add_value("titulo_interno", titulo_interno)
            loader.add_value("autor_interno", autor_interno)
            loader.add_value("titulo_competidor", card_titulo)
            loader.add_value("precio", card_precio)
            loader.add_value("precio_texto", card_precio)
            if card_imagen:
                loader.add_value("url_imagen", card_imagen)
            loader.add_value("url_libro", request.url)
            loader.add_value("fecha_extraccion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            yield loader.load_item()
