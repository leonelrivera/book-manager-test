CREATE TABLE IF NOT EXISTS precios_competidor (
    id SERIAL PRIMARY KEY,
    id_libro INTEGER NOT NULL REFERENCES libros(id) ON DELETE CASCADE,
    titulo_competidor VARCHAR(255) NOT NULL,
    autor_competidor VARCHAR(255) DEFAULT '',
    precio_web DOUBLE PRECISION NOT NULL,
    url_imagen TEXT DEFAULT '',
    formas_pago TEXT DEFAULT '',
    descripcion TEXT DEFAULT '',
    url_libro TEXT DEFAULT '',
    fecha_extraccion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_precios_competidor_libro_fecha
    ON precios_competidor(id_libro, fecha_extraccion DESC);
