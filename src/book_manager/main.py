"""Punto de entrada principal para el sistema Book Manager.

Orquesta la inicialización de los servicios mediante inyección de dependencias,
la conexión a la base de datos relacional, la precarga opcional desde scripts
SQL y la ejecución del menú interactivo en consola.
"""

import os
import sys
from typing import Optional

from book_manager.database.connection import ConexionDB
from book_manager.preload_data.preload_data import cargar_datos_desde_sql
from book_manager.repositories.repositories import (
    RepositorioAuditoria,
    RepositorioCotizacionDolar,
    RepositorioEditorial,
    RepositorioGenero,
    RepositorioLibro,
    RepositorioMoneda,
    RepositorioPrecio,
    RepositorioPrecioCompetidor,
    RepositorioStock,
    RepositorioTipoCotizacion,
)
from book_manager.services.services import BookManagerService
from book_manager.ui.console import ConsolaUI


def main(
    import_default_data: bool = False,
    ruta_sql: Optional[str] = None,
) -> BookManagerService:
    """Función principal de ejecución del sistema Book Manager.

    Args:
        import_default_data: Si es True, ejecuta la carga atómica de datos
            iniciales desde los scripts SQL ubicados en migrations/sql.
        ruta_sql: Ruta personalizada hacia un archivo o carpeta de scripts SQL.

    Returns:
        BookManagerService: Instancia del servicio central configurado.
    """
    print("🚀 Inicializando Book Manager...")

    conexion = ConexionDB.get_instancia()
    conectado = conexion.probar_conexion()
    if conectado:
        print("✅ Conexión con base de datos relacional establecida exitosamente.")
    else:
        print("⚠️ Advertencia: No se pudo verificar la conexión con la base de datos relacional.")

    repo_libro = RepositorioLibro(conexion)
    repo_genero = RepositorioGenero(conexion)
    repo_editorial = RepositorioEditorial(conexion)
    repo_moneda = RepositorioMoneda(conexion)
    repo_tipo = RepositorioTipoCotizacion(conexion)
    repo_precio = RepositorioPrecio(conexion)
    repo_precio_competidor = RepositorioPrecioCompetidor(conexion)
    repo_stock = RepositorioStock(conexion)
    repo_cotizacion = RepositorioCotizacionDolar(conexion)
    repo_auditoria = RepositorioAuditoria(conexion)

    bm_service = BookManagerService(
        repo_libro=repo_libro,
        repo_genero=repo_genero,
        repo_editorial=repo_editorial,
        repo_moneda=repo_moneda,
        repo_tipo_cotizacion=repo_tipo,
        repo_precio=repo_precio,
        repo_precio_competidor=repo_precio_competidor,
        repo_stock=repo_stock,
        repo_cotizacion=repo_cotizacion,
        repo_auditoria=repo_auditoria,
    )

    if import_default_data:
        print("📂 Cargando datos base desde scripts SQL...")
        carpeta_sql = ruta_sql or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "migrations", "sql")
        )
        resumen = cargar_datos_desde_sql(ruta_origen=carpeta_sql, conexion=conexion)
        print(f"✅ Carga SQL completada exitosamente: {resumen}")

    ui = ConsolaUI(bm_service)
    ui.iniciar_menu_interactivo()

    return bm_service


if __name__ == "__main__":
    forzar_importacion = "--import-data" in sys.argv or "-i" in sys.argv
    main(import_default_data=forzar_importacion)
