"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : api.py
SPRINT 6 : API RESTFUL FASTAPI & INTEGRATION METIER
RESPONSABLE : Mohamed Amine Aouzagh & Equipe
=============================================================================
Fournit l'API d'interconnexion entre la couche de donnees MySQL (banking_dao.py)
et l'interface web institutionnelle.
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

# Configuration CORS pour autoriser l'accès web
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
    id_mouvement: int = Field(default=1, description="ID du mouvement à tenter de modifier")
    nouveau_montant: Decimal = Field(default=Decimal("9999.00"))


# -----------------------------------------------------------------------------
# ENDPOINTS METIER
# -----------------------------------------------------------------------------

@app.get("/api/health", tags=["Système"])
def healthcheck() -> dict[str, Any]:
    """Vérification de l'état de l'API et de la connectivité au pool MySQL."""
    try:
        pool = DatabaseManager.get_pool()
        with DatabaseManager.get_cursor() as (cursor, _):
            cursor.execute("SELECT DATABASE() AS bdd, VERSION() AS ver, NOW() AS ts;")
            row = cursor.fetchone()
            return {
                "status": "UP",
                "service": "SIDPEF Core Banking API",
                "database": row["bdd"],
                "mysql_version": row["ver"],
                "server_time": str(row["ts"]),
                "connection_pool": pool.pool_name,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Base de données inaccessible : {str(e)}",
        )


@app.get("/api/clients", tags=["Clients"])
def get_all_clients() -> list[dict[str, Any]]:
    """Retourne la liste de tous les clients enregistrés pour le sélecteur d'utilisateurs."""
    query = """
        SELECT cl.num_client, cl.nom, cl.prenom, cl.cin, cl.email, cl.telephone,
               COUNT(c.id_contrepartie) AS nb_comptes,
               COALESCE(SUM(c.solde), 0.00) AS solde_total
        FROM client cl
        LEFT JOIN titulariser t ON cl.num_client = t.num_client
        LEFT JOIN compte c      ON t.id_contrepartie_compte = c.id_contrepartie
        GROUP BY cl.num_client, cl.nom, cl.prenom, cl.cin, cl.email, cl.telephone
        ORDER BY cl.num_client;
    """
    with DatabaseManager.get_cursor() as (cursor, _):
        cursor.execute(query)
        return cursor.fetchall()


@app.get("/api/clients/{cin}", tags=["Clients"])
def get_client_profile(cin: str) -> dict[str, Any]:
    """Vue consolidée 360° du client, de ses comptes, cartes et soldes."""
    try:
        profil = BankingDAO.get_client_by_cin(cin)
        client = profil["client"]
        return {
            "client": {
                "num_client": client.num_client,
                "nom": client.nom,
                "prenom": client.prenom,
                "cin": client.cin,
                "email": client.email,
                "telephone": client.telephone,
                "date_naissance": str(client.date_naissance) if client.date_naissance else None,
            },
            "comptes": profil["comptes"],
            "cartes": profil["cartes"],
        }
    except BankingException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get("/api/comptes", tags=["Comptes"])
def get_all_comptes() -> list[dict[str, Any]]:
    """Retourne l'ensemble des comptes actifs pour les listes déroulantes de virement."""
    query = """
        SELECT c.id_contrepartie AS num_compte, 
               CONCAT(cl.prenom, ' ', cl.nom) AS titulaire,
               cl.cin,
               c.solde, 
               c.decouvert_autorise, 
               tc.libelle AS type_compte,
               ag.nom_agence
        FROM compte c
        JOIN titulariser t ON c.id_contrepartie = t.id_contrepartie_compte
        JOIN client cl     ON t.num_client = cl.num_client
        JOIN type_compte tc ON c.code_type = tc.code_type
        JOIN agence ag     ON c.code_agence = ag.code_agence
        ORDER BY c.id_contrepartie;
    """
    with DatabaseManager.get_cursor() as (cursor, _):
        cursor.execute(query)
        return cursor.fetchall()


@app.get("/api/comptes/{id_compte}/releve", tags=["Comptes"])
def get_releve_compte(id_compte: int) -> list[dict[str, Any]]:
    """Génère le relevé de compte chronologique avec solde progressif calculé par Window Function."""
    try:
        lignes = BankingDAO.get_releve_chronologique(id_compte)
        return [
            {
                "id_mouvement": l.id_mouvement,
                "date_valeur": str(l.date_valeur),
                "date_heure": str(l.date_heure),
                "ref_transaction": l.ref_transaction,
                "libelle_operation": l.libelle_operation,
                "canal": l.canal,
                "debit": float(l.debit) if l.debit is not None else None,
                "credit": float(l.credit) if l.credit is not None else None,
                "solde_cumule": float(l.solde_cumule),
            }
            for l in lignes
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/virements", tags=["Virements"], response_model=VirementResponse)
def executer_virement(req: VirementRequest) -> VirementResponse:
    """
    Exécute un virement interne atomique avec validation de la partie double
    et contrôle de solvabilité via la procédure stockée MySQL SP_VALIDER_TRANSACTION.
    """
    try:
        ref_tx = BankingDAO.executer_virement(
            compte_source_id=req.compte_source_id,
            compte_dest_id=req.compte_dest_id,
            montant=req.montant,
            canal=req.canal,
            ip_source="127.0.0.1",
        )
        return VirementResponse(
            success=True,
            ref_transaction=ref_tx,
            message=f"Virement de {req.montant:,.2f} MAD validé avec succès (Réf: {ref_tx}).",
            compte_source_id=req.compte_source_id,
            compte_dest_id=req.compte_dest_id,
            montant=float(req.montant),
        )
    except InsufficientFundsError as e:
        # Erreur métier : Découvert non autorisé (Code HTTP 400 clair pour la bannière)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rejet Bancaire : Provision insuffisante pour le compte N°{req.compte_source_id}. "
                   f"L'opération dépasserait le découvert autorisé. Aucun montant n'a été débité.",
        )
    except AccountNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BankingException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne du système transactionnel : {str(e)}",
        )


@app.get("/api/audit/anomalies", tags=["Audit & Sécurité"])
def get_anomalies_audit() -> list[dict[str, Any]]:
    """Extrait l'ensemble des transactions rejetées ou en attente pour la supervision administrative."""
    try:
        anomalies = BankingDAO.get_anomalies_du_jour()
        return [
            {
                "ref_transaction": a["ref_transaction"],
                "date_heure": str(a["date_heure"]),
                "statut_trans": a["statut_trans"],
                "type_transaction": a["type_transaction"],
                "canal": a["canal"],
                "ip_source": a["ip_source"],
                "montant_operation": float(a["montant_operation"]),
            }
            for a in anomalies
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/audit/test-trigger", tags=["Audit & Sécurité"])
def tester_trigger_immuabilite(req: TriggerTestRequest) -> dict[str, Any]:
    """
    Tente délibérément de modifier un mouvement existant pour prouver en temps réel
    que le trigger MySQL 8+ BEFORE UPDATE intercepte et bloque l'altération.
    """
    try:
        BankingDAO.tenter_modifier_mouvement(req.id_mouvement, req.nouveau_montant)
        return {
            "status": "FAIL_SECURITY",
            "message": "ALERTE : Le trigger n'a pas réagi ! La modification est passée.",
        }
    except AccountingImmutabilityError as e:
        return {
            "status": "TRIGGER_BLOCKED_SUCCESS",
            "code_sqlstate": "45000",
            "code_erreur_mysql": 1644,
            "trigger_name": "trg_mouvement_before_update",
            "message_interception": str(e),
            "piste_audit": "Inviolabilité comptable garantie. La base de données a rejeté l'écriture.",
        }


# -----------------------------------------------------------------------------
# POINT D'ENTREE API REST
# -----------------------------------------------------------------------------
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
