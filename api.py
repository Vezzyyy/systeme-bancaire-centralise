"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : api.py
SPRINT 6 : API RESTFUL FASTAPI & INTEGRATION METIER
RESPONSABLE : Mohamed Amine Aouzagh & Yassine Chaouri
=============================================================================
Fournit l'API d'interconnexion entre la couche de donnees MySQL (banking_dao.py)
et les services bancaires RESTful.
=============================================================================
"""

from decimal import Decimal
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from banking_dao import BankingDAO
from database import DatabaseManager
from models import (
    AccountNotFoundError,
    AccountingImmutabilityError,
    BankingException,
    InsufficientFundsError,
)

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


# -----------------------------------------------------------------------------
# ENDPOINTS METIER : CLIENTS & COMPTES (Yassine Chaouri)
# -----------------------------------------------------------------------------
@app.get("/api/clients", tags=["Clients & Comptes"])
def list_clients() -> list[dict[str, Any]]:
    """Récupère l'ensemble des clients enregistrés avec domiciliation d'agence."""
    try:
        with DatabaseManager.get_cursor(dictionary=True) as cursor:
            query = """
                SELECT c.idClient, c.cin, c.nom, c.prenom, c.email, c.telephone,
                       a.nomAgence, a.codeGuichet
                FROM CLIENT c
                JOIN AGENCE a ON c.idAgence = a.idAgence
                ORDER BY c.idClient ASC;
            """
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/clients/{cin}", tags=["Clients & Comptes"])
def get_client_profile(cin: str) -> dict[str, Any]:
    """Extrait la vue 360° du client : identité, comptes, cartes associées et solde consolidé."""
    try:
        profile = BankingDAO.get_vue_360_client(cin)
        if not profile or not profile.get("client"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client avec le CIN '{cin}' introuvable dans le système bancaire.",
            )

        client_dict = {
            "idClient": profile["client"].id_client,
            "cin": profile["client"].cin,
            "nom": profile["client"].nom,
            "prenom": profile["client"].prenom,
            "email": profile["client"].email,
            "telephone": profile["client"].telephone,
            "idAgence": profile["client"].id_agence,
        }

        comptes_list = [
            {
                "idCompte": cp.id_compte,
                "rib": cp.rib,
                "type_libelle": cp.type_libelle,
                "solde": float(cp.solde),
                "decouvertAutorise": float(cp.decouvert_autorise),
                "plafondVirement": float(cp.plafond_virement),
                "role_titularite": cp.role_titularite,
                "devise": cp.devise,
            }
            for cp in profile["comptes"]
        ]

        cartes_list = [
            {
                "idCarte": c.id_carte,
                "numero_masque": f"•••• •••• •••• {c.numero[-4:]}" if len(c.numero) >= 4 else c.numero,
                "typeCarte": c.type_carte,
                "dateExpiration": str(c.date_expiration),
                "plafondRetraitHebdo": float(c.plafond_retrait_hebdo),
                "plafondPaiementMensuel": float(c.plafond_paiement_mensuel),
                "estActive": c.est_active,
                "compte_associe_rib": c.compte_associe_rib,
            }
            for c in profile["cartes"]
        ]

        return {
            "client": client_dict,
            "comptes": comptes_list,
            "cartes": cartes_list,
            "solde_total_consolide": float(profile["solde_total_consolide"]),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/comptes/{id_compte}/releve", tags=["Clients & Comptes"])
def get_releve_compte(id_compte: int) -> list[dict[str, Any]]:
    """Génère le relevé chronologique avec solde cumulé ligne par ligne (SUM() OVER)."""
    try:
        entries = BankingDAO.get_releve_chronologique(id_compte)
        return [
            {
                "ref_transaction": e.ref_transaction,
                "date_heure": str(e.date_heure),
                "type_libelle": e.type_libelle,
                "sens": e.sens,
                "montant": float(e.montant),
                "solde_cumule": float(e.solde_cumule),
                "libelle": e.libelle,
            }
            for e in entries
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
