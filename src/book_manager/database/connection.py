"""Módulo de conexión y gestión transaccional con SQLAlchemy para Book Manager.

Proporciona la clase ConexionDB para administrar el motor de base de datos
(Engine), la fábrica de sesiones (sessionmaker) y la conectividad con Supabase
(PostgreSQL) u otros motores relacionales compatibles con SQLAlchemy.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


class ConexionDB:
    """Administrador centralizado de la conexión a la base de datos con SQLAlchemy.

    Implementa el patrón Singleton para reutilizar el motor (Engine) y el grupo de
    conexiones (connection pool), soportando configuración mediante variables de entorno
    (.env) para Supabase (PostgreSQL) o almacenamiento local de respaldo (SQLite).
    """

    _instancia: Optional["ConexionDB"] = None

    def __init__(self, database_url: Optional[str] = None) -> None:
        """Inicializa la conexión a la base de datos y la fábrica de sesiones.

        Args:
            database_url: Cadena de conexión opcional. Si no se provee, se obtiene
                de la variable de entorno DATABASE_URL (.env). Si no existe, se
                utiliza una base de datos local SQLite como respaldo.
        """
        load_dotenv()

        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///book_manager.db")

        # Corrección de prefijo para compatibilidad con SQLAlchemy 2.0 y psycopg2
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        self._database_url: str = database_url

        # Configuración del motor: pool_pre_ping previene conexiones caídas en servicios cloud como Supabase
        connect_args = {}
        if self._database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self._engine: Engine = create_engine(
            self._database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

        self._session_factory: sessionmaker[Session] = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @classmethod
    def get_instancia(cls, database_url: Optional[str] = None) -> "ConexionDB":
        """Obtiene o inicializa la instancia única (Singleton) de ConexionDB.

        Args:
            database_url: Cadena de conexión opcional para inicializar o cambiar.

        Returns:
            ConexionDB: La instancia única de la conexión a la base de datos.
        """
        if cls._instancia is None or database_url is not None:
            cls._instancia = cls(database_url=database_url)
        return cls._instancia

    @property
    def database_url(self) -> str:
        """Retorna la cadena de conexión configurada (sin exponer credenciales sensibles)."""
        return self._database_url

    @property
    def engine(self) -> Engine:
        """Retorna el motor (Engine) de SQLAlchemy."""
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Retorna la fábrica de sesiones (sessionmaker) configurada."""
        return self._session_factory

    def crear_sesion(self) -> Session:
        """Crea y retorna una nueva sesión de SQLAlchemy.

        Returns:
            Session: Sesión activa para interactuar con la base de datos.
        """
        return self._session_factory()

    def probar_conexion(self) -> bool:
        """Verifica la conectividad con la base de datos ejecutando una consulta elemental.

        Returns:
            bool: True si la conexión fue exitosa, False en caso de error.
        """
        try:
            with self._engine.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as error:
            print(f"⚠️ Error al conectar con la base de datos: {error}")
            return False
