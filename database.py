"""
Gestionnaire de connexion à MySQL avec pool de connexions et context managers.
Assure la libération systématique des ressources et l'isolation transactionnelle.
"""

from contextlib import contextmanager
from typing import Generator
import mysql.connector
from mysql.connector import pooling
from config import config


class DatabaseManager:
    _pool: pooling.MySQLConnectionPool | None = None

    @classmethod
    def get_pool(cls) -> pooling.MySQLConnectionPool:
        """Initialise ou retourne le pool de connexions MySQL."""
        if cls._pool is None:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name=config.pool_name,
                pool_size=config.pool_size,
                pool_reset_session=True,
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                autocommit=False,
            )
        return cls._pool

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator[mysql.connector.connection.MySQLConnection, None, None]:
        """
        Fournit une connexion issue du pool sous forme de context manager.
        Garantit que la connexion est refermee (restituee au pool) a la sortie.
        """
        pool = cls.get_pool()
        conn = pool.get_connection()
        try:
            yield conn
        finally:
            if conn.is_connected():
                conn.close()

    @classmethod
    @contextmanager
    def get_cursor(cls, dictionary: bool = True):
        """
        Fournit un curseur et gere automatiquement les transactions (commit/rollback).
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor(dictionary=dictionary)
            try:
                yield cursor, conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
