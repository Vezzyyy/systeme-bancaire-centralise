"""
Configuration de la connexion à la base de données bancaire.
Isole les identifiants sensibles via des variables d'environnement.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "3306"))
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "root")
    database: str = os.getenv("DB_NAME", "banque_centrale_db")
    pool_name: str = "banque_pool"
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))


# Instance globale de configuration
config = DatabaseConfig()
