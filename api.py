"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : api.py
SPRINT 6 : API RESTFUL FASTAPI & INTEGRATION METIER
RESPONSABLE : Mohamed Amine Aouzagh
=============================================================================
Initialisation du serveur d'application FastAPI, configuration des middlewares
CORS et definition des schemas de validation Pydantic V2.
=============================================================================
"""

from decimal import Decimal
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from database import DatabaseManager

# -----------------------------------------------------------------------------
# APPLICATION FASTAPI
# -----------------------------------------------------------------------------
app = FastAPI(
    title="SIDPEF — Système Bancaire Centralisé API",
    description="API RESTful institutionnelle pour la gestion des comptes, virements et piste d'audit.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configuration CORS pour autoriser les requêtes clients et services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# SCHEMAS PYDANTIC V2
# -----------------------------------------------------------------------------
class VirementRequest(BaseModel):
    compte_source_id: int = Field(..., description="Identifiant du compte à débiter")
    compte_dest_id: int = Field(..., description="Identifiant du compte à créditer")
    montant: Decimal = Field(..., gt=0, decimal_places=2, description="Montant strictement positif en MAD")
    canal: str = Field(default="WEB", description="Canal d'initiation (WEB, MOBILE, GUICHET, GAB, TPE)")


class VirementResponse(BaseModel):
    success: bool
    ref_transaction: str
    message: str
    compte_source_id: int
    compte_dest_id: int
    montant: float


class TriggerTestRequest(BaseModel):
    id_mouvement: int = Field(default=1, description="Identifiant du mouvement comptable à tenter de modifier")
    nouveau_montant: Decimal = Field(default=Decimal("9999.00"), description="Nouveau montant illégal")


# -----------------------------------------------------------------------------
# ENDPOINTS SYSTEME & SANTE
# -----------------------------------------------------------------------------
@app.get("/api/health", tags=["Système"])
def health_check() -> dict[str, Any]:
    """Contrôle la connectivité avec le pool MySQL 8+ et l'intégrité du service."""
    try:
        with DatabaseManager.get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT DATABASE() AS db_name, @@version AS mysql_version, NOW() AS server_time;")
            row = cursor.fetchone()
            return {
                "status": "UP",
                "database": row["db_name"],
                "mysql_version": row["mysql_version"],
                "server_time": str(row["server_time"]),
                "pool_status": "ONLINE",
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Échec de connexion à la base de données : {str(e)}",
        )


@app.get("/", tags=["Système"])
def root() -> dict[str, str]:
    """Point d'entrée racine de l'API bancaire."""
    return {
        "service": "SIDPEF Core Banking API",
        "documentation": "/api/docs",
        "status": "ONLINE",
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
