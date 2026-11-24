"""Definición de modelos de datos (Items) para el scraper de libros competidores.

Define la estructura de los elementos extraídos de sitios de librerías online
como Cúspide para su posterior validación, persistencia y comparación.
"""

import scrapy


class LibroCompetidorItem(scrapy.Item):
    """Item que representa los datos extraídos de un libro de la competencia.

    Campos:
        id_libro: Identificador del libro correspondiente en el catálogo propio.
        titulo_interno: Título del libro correspondiente en el catálogo propio.
        autor_interno: Autor correspondiente en el catálogo propio.
        titulo_competidor: Título publicado en el sitio del competidor.
        autor_competidor: Autor extraído de la publicación del competidor.
        precio: Precio actual normalizado a float.
        precio_texto: Precio en texto tal como aparece en la web.
        url_imagen: URL absoluta de la portada del libro, si existe.
        formas_pago: Opciones de financiación y formas de pago, si existen.
        descripcion: Sinopsis o descripción detallada del libro, si existe.
        url_libro: Enlace a la ficha individual del libro.
        fecha_extraccion: Fecha y hora de la extracción.
    """

    id_libro = scrapy.Field()
    titulo_interno = scrapy.Field()
    autor_interno = scrapy.Field()
    titulo_competidor = scrapy.Field()
    autor_competidor = scrapy.Field()
    precio = scrapy.Field()
    precio_texto = scrapy.Field()
    url_imagen = scrapy.Field()
    formas_pago = scrapy.Field()
    descripcion = scrapy.Field()
    url_libro = scrapy.Field()
    fecha_extraccion = scrapy.Field()
