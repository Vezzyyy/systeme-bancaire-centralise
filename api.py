"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : api.py
SPRINT 7 : SYSTEME D'AUTHENTIFICATION JWT, RBAC & API SECURISEE
RESPONSABLE : Equipe Projet (Yassine, Saad, Hamza, Mouad, Mohamed Amine)
=============================================================================
Fournit l'API d'authentification bancaire OAuth2 / JWT, le contrôle d'accès
fondé sur les rôles (RBAC) et l'interconnexion sécurisée avec MySQL 8+.
=============================================================================
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from typing import Any, Optional
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
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
# CONFIGURATION DE SECURITE JWT (STANDARDS BANCAIRES)
# -----------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "sidpef-banking-production-security-token-secret-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # Durée de validité de 8 heures (session de travail)

http_bearer = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Génère un jeton JWT signé avec date d'expiration et métadonnées RBAC."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# -----------------------------------------------------------------------------
# APPLICATION FASTAPI
# -----------------------------------------------------------------------------
app = FastAPI(
    title="SIDPEF — Système Bancaire Centralisé API",
    description="API RESTful institutionnelle sécurisée par JWT, RBAC et intégrité MySQL 8+.",
    version="1.1.0",
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

# Montage des fichiers statiques de l'application web si présents
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------------------------------------------------
# SCHEMAS PYDANTIC V2
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., description="Email bancaire ou CIN du client/administrateur")
    password: str = Field(..., description="Mot de passe secret")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


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
# DEPENDANCES D'AUTHENTIFICATION & CONTROLE D'ACCES (RBAC)
# -----------------------------------------------------------------------------
def get_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    token_oauth: Optional[str] = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """
    Extrait et valide le jeton JWT transmis via header Authorization: Bearer <token>.
    Résout l'utilisateur en base de données et garantit l'intégrité de la session.
    """
    token = None
    if auth and auth.credentials:
        token = auth.credentials
    elif token_oauth:
        token = token_oauth
    else:
        raw_header = request.headers.get("Authorization", "")
        if raw_header.startswith("Bearer "):
            token = raw_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accès non authentifié : jeton JWT Bearer absent.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        cin: Optional[str] = payload.get("cin") or payload.get("sub")
        if not cin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeton JWT invalide : identifiant bancaire manquant.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée : veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton de sécurité invalide ou falsifié.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = BankingDAO.get_user_by_cin(cin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur bancaire introuvable dans la base centrale.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    token_oauth: Optional[str] = Depends(oauth2_scheme),
) -> Optional[dict[str, Any]]:
    """Tente de résoudre l'utilisateur si un jeton est présent, sinon renvoie None sans lever d'erreur."""
    try:
        return get_current_user(request, auth, token_oauth)
    except HTTPException:
        return None


def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Garantit que l'utilisateur dispose du rôle privilégié ADMIN (RBAC)."""
    if str(current_user.get("role", "")).upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit : cette opération est strictement réservée au Back-Office Administrateur.",
        )
    return current_user


# -----------------------------------------------------------------------------
# ENDPOINTS D'AUTHENTIFICATION (SPRINT 7)
# -----------------------------------------------------------------------------
@app.post("/api/auth/login", tags=["Authentification"], response_model=TokenResponse)
def login_json(credentials: LoginRequest) -> TokenResponse:
    """
    Authentifie un client ou un administrateur à partir de son email ou CIN et de son mot de passe.
    Retourne le jeton JWT signé avec les permissions du rôle.
    """
    user = BankingDAO.authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants bancaires incorrects (Email/CIN ou mot de passe erroné).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": user["cin"],
        "cin": user["cin"],
        "email": user["email"],
        "role": user["role"],
        "nom": user["nom"],
        "prenom": user["prenom"],
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )


@app.post("/api/auth/token", tags=["Authentification"], include_in_schema=False)
def login_oauth2_form(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    """Support standard OAuth2 Password Request Form pour Swagger UI."""
    user = BankingDAO.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({
        "sub": user["cin"],
        "cin": user["cin"],
        "email": user["email"],
        "role": user["role"],
    })
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/me", tags=["Authentification"])
def get_current_user_profile(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Retourne l'identité et le rôle de l'utilisateur actuellement connecté."""
    return user


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
    """Retourne la liste des clients enregistrés pour le répertoire bancaire."""
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
def get_client_profile(
    cin: str,
    current_user: Optional[dict[str, Any]] = Depends(get_optional_current_user),
) -> dict[str, Any]:
    """
    Vue consolidée 360° du client, de ses comptes, cartes et soldes.
    Si un utilisateur est connecté avec un rôle CLIENT, il ne peut consulter que son propre profil.
    """
    if current_user:
        user_role = str(current_user.get("role", "")).upper()
        user_cin = str(current_user.get("cin", "")).upper()
        if user_role != "ADMIN" and user_cin != cin.strip().upper():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : vous n'êtes pas autorisé à consulter les données bancaires du client {cin}.",
            )

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
                "role": getattr(client, "role", "CLIENT"),
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
def get_anomalies_audit(
    current_user: Optional[dict[str, Any]] = Depends(get_optional_current_user),
) -> list[dict[str, Any]]:
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
# POINT D'ENTREE RACINE (APPLICATION WEB OU API STATUS)
# -----------------------------------------------------------------------------
@app.get("/", tags=["Système"], include_in_schema=False)
def root():
    """Point d'entrée racine : sert l'application web SIDPEF ou les métadonnées de l'API."""
    for candidate in [
        os.path.join("static", "index.html"),
        os.path.join("sidpef-—-intranet-bancaire-centralisé", "index.html"),
    ]:
        if os.path.exists(candidate):
            return FileResponse(candidate)
    return {
        "service": "SIDPEF Core Banking API",
        "documentation": "/api/docs",
        "status": "ONLINE",
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
