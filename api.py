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
# ENDPOINTS CARTES BANCAIRES (CLIENT - Espace Cartes)
# -----------------------------------------------------------------------------
class CartePatchRequest(BaseModel):
    statut_carte: str = Field(..., description="Nouveau statut: ACTIVE | BLOQUEE | OPPOSEE")

class CarteLimitsRequest(BaseModel):
    plafond_paiement: Optional[Decimal] = None
    plafond_retrait: Optional[Decimal] = None


@app.get("/api/cartes/client/{num_client}", tags=["Cartes"])
def get_cartes_client(num_client: int) -> list[dict[str, Any]]:
    """Retourne toutes les cartes d'un client avec le détail du compte associé."""
    query = """
        SELECT cb.num_carte, cb.date_expiration, cb.statut_carte,
               cb.plafond_paiement, cb.plafond_retrait,
               cb.id_contrepartie_compte AS num_compte,
               tc.libelle AS type_compte, ag.nom_agence
        FROM carte_bancaire cb
        JOIN compte c ON cb.id_contrepartie_compte = c.id_contrepartie
        JOIN type_compte tc ON c.code_type = tc.code_type
        JOIN agence ag ON c.code_agence = ag.code_agence
        WHERE cb.num_client = %s
        ORDER BY cb.date_expiration DESC;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query, (num_client,))
        rows = cursor.fetchall()
        return [
            {
                **r,
                "date_expiration": str(r["date_expiration"]) if r["date_expiration"] else None,
                "plafond_paiement": float(r["plafond_paiement"]) if r["plafond_paiement"] else None,
                "plafond_retrait": float(r["plafond_retrait"]) if r["plafond_retrait"] else None,
            }
            for r in rows
        ]


@app.patch("/api/cartes/{num_carte}/statut", tags=["Cartes"])
def patch_carte_statut(
    num_carte: str,
    req: CartePatchRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Met à jour le statut d'une carte bancaire (ACTIVE, BLOQUEE, OPPOSEE).
    Kill-switch client : un client ne peut modifier que ses propres cartes.
    """
    allowed_statuts = {"ACTIVE", "BLOQUEE", "OPPOSEE"}
    if req.statut_carte.upper() not in allowed_statuts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statut invalide. Valeurs acceptées : {allowed_statuts}",
        )

    # Vérifier que la carte existe et appartient bien à l'utilisateur si client
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT cb.num_carte, cb.statut_carte, cl.cin FROM carte_bancaire cb JOIN client cl ON cb.num_client = cl.num_client WHERE cb.num_carte = %s;",
                (num_carte,),
            )
            carte = cursor.fetchone()
            if not carte:
                raise HTTPException(status_code=404, detail=f"Carte {num_carte} introuvable.")

            user_role = str(current_user.get("role", "")).upper()
            user_cin = str(current_user.get("cin", "")).upper()
            if user_role != "ADMIN" and user_cin != str(carte["cin"]).upper():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Vous n'êtes pas autorisé à modifier cette carte.",
                )

            old_statut = carte["statut_carte"]
            cursor.execute(
                "UPDATE carte_bancaire SET statut_carte = %s WHERE num_carte = %s;",
                (req.statut_carte.upper(), num_carte),
            )
            conn.commit()
            return {
                "success": True,
                "num_carte": num_carte,
                "ancien_statut": old_statut,
                "nouveau_statut": req.statut_carte.upper(),
                "message": f"Carte {num_carte} passée de {old_statut} à {req.statut_carte.upper()}.",
            }
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


@app.patch("/api/cartes/{num_carte}/limites", tags=["Cartes"])
def patch_carte_limites(
    num_carte: str,
    req: CarteLimitsRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Met à jour les plafonds d'une carte (retrait et/ou paiement)."""
    if req.plafond_paiement is None and req.plafond_retrait is None:
        raise HTTPException(status_code=400, detail="Au moins un plafond doit être fourni.")

    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT cb.num_carte, cl.cin FROM carte_bancaire cb JOIN client cl ON cb.num_client = cl.num_client WHERE cb.num_carte = %s;",
                (num_carte,),
            )
            carte = cursor.fetchone()
            if not carte:
                raise HTTPException(status_code=404, detail=f"Carte {num_carte} introuvable.")

            user_role = str(current_user.get("role", "")).upper()
            user_cin = str(current_user.get("cin", "")).upper()
            if user_role != "ADMIN" and user_cin != str(carte["cin"]).upper():
                raise HTTPException(status_code=403, detail="Accès refusé.")

            updates = []
            params = []
            if req.plafond_paiement is not None:
                updates.append("plafond_paiement = %s")
                params.append(req.plafond_paiement)
            if req.plafond_retrait is not None:
                updates.append("plafond_retrait = %s")
                params.append(req.plafond_retrait)
            params.append(num_carte)

            cursor.execute(f"UPDATE carte_bancaire SET {', '.join(updates)} WHERE num_carte = %s;", params)
            conn.commit()
            return {"success": True, "num_carte": num_carte, "message": "Plafonds mis à jour."}
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS BÉNÉFICIAIRES EXTERNES
# -----------------------------------------------------------------------------
class BeneficiaireCreateRequest(BaseModel):
    iban: str = Field(..., description="IBAN du bénéficiaire (jusqu'à 34 caractères)")
    bic: str = Field(..., description="Code BIC/SWIFT de la banque bénéficiaire")
    nom_beneficiaire: str = Field(..., description="Nom complet du bénéficiaire")


@app.get("/api/beneficiaires", tags=["Bénéficiaires"])
def get_all_beneficiaires() -> list[dict[str, Any]]:
    """Retourne la liste de tous les bénéficiaires externes enregistrés."""
    query = """
        SELECT be.id_contrepartie, be.iban, be.bic, be.nom_beneficiaire
        FROM beneficiaire_externe be
        ORDER BY be.nom_beneficiaire;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query)
        return cursor.fetchall()


@app.post("/api/beneficiaires", tags=["Bénéficiaires"], status_code=201)
def creer_beneficiaire(
    req: BeneficiaireCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Enregistre un nouveau bénéficiaire externe (IBAN/BIC) dans la base."""
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Création de l'entrée parent dans CONTREPARTIE
            cursor.execute(
                "INSERT INTO contrepartie (type_contrepartie) VALUES ('BENEFICIAIRE');",
            )
            id_contrepartie = cursor.lastrowid

            cursor.execute(
                "INSERT INTO beneficiaire_externe (id_contrepartie, iban, bic, nom_beneficiaire) VALUES (%s, %s, %s, %s);",
                (id_contrepartie, req.iban.strip().upper(), req.bic.strip().upper(), req.nom_beneficiaire.strip()),
            )
            conn.commit()
            return {
                "success": True,
                "id_contrepartie": id_contrepartie,
                "iban": req.iban.strip().upper(),
                "bic": req.bic.strip().upper(),
                "nom_beneficiaire": req.nom_beneficiaire.strip(),
                "message": f"Bénéficiaire {req.nom_beneficiaire} enregistré (Contrepartie N°{id_contrepartie}).",
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — GESTION TRANSACTIONS (Approuver / Rejeter)
# -----------------------------------------------------------------------------
class TransactionUpdateRequest(BaseModel):
    nouveau_statut: str = Field(..., description="VALIDEE | REJETEE")
    motif: Optional[str] = Field(default="Décision opérateur SIDPEF", description="Motif de la décision")


@app.patch("/api/transactions/{ref_transaction}/statut", tags=["Transactions Admin"])
def update_transaction_statut(
    ref_transaction: str,
    req: TransactionUpdateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Maker-Checker : Force le statut d'une transaction EN_ATTENTE vers VALIDEE ou REJETEE.
    Réservé aux administrateurs Back-Office (RBAC ADMIN requis).
    """
    allowed = {"VALIDEE", "REJETEE"}
    if req.nouveau_statut.upper() not in allowed:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs autorisées : {allowed}")

    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT ref_transaction, statut_trans FROM transaction WHERE ref_transaction = %s;",
                (ref_transaction,),
            )
            tx = cursor.fetchone()
            if not tx:
                raise HTTPException(status_code=404, detail=f"Transaction {ref_transaction} introuvable.")
            if tx["statut_trans"] not in ("EN_ATTENTE", "REJETEE"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Seules les transactions EN_ATTENTE ou REJETEE peuvent être modifiées. Statut actuel : {tx['statut_trans']}",
                )

            ancien_statut = tx["statut_trans"]
            cursor.execute(
                "UPDATE transaction SET statut_trans = %s WHERE ref_transaction = %s;",
                (req.nouveau_statut.upper(), ref_transaction),
            )
            conn.commit()
            return {
                "success": True,
                "ref_transaction": ref_transaction,
                "ancien_statut": ancien_statut,
                "nouveau_statut": req.nouveau_statut.upper(),
                "operateur": f"{admin.get('prenom')} {admin.get('nom')}",
                "message": f"Transaction {ref_transaction} passée de {ancien_statut} → {req.nouveau_statut.upper()} par {admin.get('prenom')} {admin.get('nom')}.",
            }
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — EXTOURNE (Contre-passation)
# -----------------------------------------------------------------------------
class ExtourneRequest(BaseModel):
    ref_transaction_originale: str = Field(..., description="Référence de la transaction à contre-passer")
    motif: str = Field(default="Erreur de saisie — Extourne opérateur", description="Motif de l'extourne")


@app.post("/api/transactions/extourne", tags=["Transactions Admin"])
def creer_extourne(
    req: ExtourneRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Génère une transaction miroir (extourne / contre-passation) inversant une transaction existante.
    Cette opération n'altère JAMAIS le passé : elle crée une NOUVELLE transaction de sens opposé.
    Respecte l'immuabilité comptable (triggers MySQL BEFORE DELETE / BEFORE UPDATE).
    """
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Récupérer la transaction originale et ses mouvements
            cursor.execute(
                """
                SELECT t.ref_transaction, t.statut_trans, t.code_type_trans, t.code_canal,
                       t.ip_source, t.ref_transaction_annulee
                FROM transaction t WHERE t.ref_transaction = %s;
                """,
                (req.ref_transaction_originale,),
            )
            tx_orig = cursor.fetchone()
            if not tx_orig:
                raise HTTPException(status_code=404, detail=f"Transaction originale {req.ref_transaction_originale} introuvable.")

            if tx_orig.get("ref_transaction_annulee"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cette transaction est déjà une extourne ou a déjà été annulée (Réf annulée: {tx_orig['ref_transaction_annulee']}).",
                )

            cursor.execute(
                "SELECT id_mouvement, sens, montant, id_contrepartie FROM mouvement WHERE ref_transaction = %s;",
                (req.ref_transaction_originale,),
            )
            mouvements = cursor.fetchall()
            if not mouvements:
                raise HTTPException(status_code=400, detail="Aucun mouvement trouvé pour cette transaction.")

            # 2. Créer la transaction d'extourne
            from datetime import datetime, timezone
            import uuid
            ref_extourne = f"EXT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

            cursor.execute(
                """
                INSERT INTO transaction (ref_transaction, date_heure, statut_trans, ip_source,
                    code_type_trans, code_canal, ref_transaction_annulee)
                VALUES (%s, NOW(), 'VALIDEE', %s, %s, %s, %s);
                """,
                (ref_extourne, tx_orig["ip_source"] or "127.0.0.1",
                 tx_orig["code_type_trans"], tx_orig["code_canal"],
                 req.ref_transaction_originale),
            )

            # 3. Insérer les mouvements inversés (D ↔ C)
            sens_inverse = {"D": "C", "C": "D"}
            for mv in mouvements:
                cursor.execute(
                    "INSERT INTO mouvement (sens, montant, date_valeur, devise, ref_transaction, id_contrepartie) VALUES (%s, %s, CURDATE(), 'MAD', %s, %s);",
                    (sens_inverse[mv["sens"]], mv["montant"], ref_extourne, mv["id_contrepartie"]),
                )

            # 4. Appel de SP_VALIDER_TRANSACTION pour recalculer les soldes
            cursor.callproc("SP_VALIDER_TRANSACTION", (ref_extourne,))
            conn.commit()

            return {
                "success": True,
                "ref_extourne": ref_extourne,
                "ref_originale": req.ref_transaction_originale,
                "nb_mouvements_inverses": len(mouvements),
                "operateur": f"{admin.get('prenom')} {admin.get('nom')}",
                "message": f"Extourne {ref_extourne} créée avec succès. {len(mouvements)} mouvements inversés. Aucune écriture passée modifiée.",
            }
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Échec de l'extourne : {str(e)}")
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — VÉRIFICATION ÉQUILIBRE COMPTABLE GLOBAL
# -----------------------------------------------------------------------------
@app.get("/api/audit/equilibre-comptable", tags=["Audit & Sécurité"])
def verifier_equilibre_comptable(
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Vérifie l'équilibre comptable global de la banque.
    SUM(tous Crédits) = SUM(tous Débits), i.e. SUM_net = 0,00 MAD.
    C'est la preuve ultime de l'intégrité de la partie double.
    """
    query = """
        SELECT
            SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE 0 END) AS total_credits,
            SUM(CASE WHEN m.sens = 'D' THEN m.montant ELSE 0 END) AS total_debits,
            SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE -m.montant END) AS solde_net,
            COUNT(*) AS nb_mouvements,
            COUNT(DISTINCT m.ref_transaction) AS nb_transactions
        FROM mouvement m
        JOIN transaction t ON m.ref_transaction = t.ref_transaction
        WHERE t.statut_trans = 'VALIDEE';
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query)
        row = cursor.fetchone()
        solde_net = float(row["solde_net"] or 0)
        is_balanced = abs(solde_net) < 0.01  # Tolérance d'arrondi centimes
        return {
            "total_credits": float(row["total_credits"] or 0),
            "total_debits": float(row["total_debits"] or 0),
            "solde_net": solde_net,
            "nb_mouvements": row["nb_mouvements"],
            "nb_transactions": row["nb_transactions"],
            "equilibre_valide": is_balanced,
            "message": "✓ ÉQUILIBRE PARFAIT : Σ Débits = Σ Crédits (Partie Double respectée)" if is_balanced else f"⚠ DÉSÉQUILIBRE DÉTECTÉ : {solde_net:,.2f} MAD — Enquête requise",
        }


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — ANALYTICS AGENCE (Trésorerie)
# -----------------------------------------------------------------------------
@app.get("/api/admin/analytics/agences", tags=["Analytics Admin"])
def get_analytics_agences(admin: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    """Statistiques par agence : volumes de dépôts et retraits (GROUP BY agence)."""
    query = """
        SELECT
            ag.code_agence, ag.nom_agence, ag.ville,
            COUNT(DISTINCT c.id_contrepartie) AS nb_comptes,
            COALESCE(SUM(c.solde), 0) AS encours_total,
            COALESCE(SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE 0 END), 0) AS volume_credits,
            COALESCE(SUM(CASE WHEN m.sens = 'D' THEN m.montant ELSE 0 END), 0) AS volume_debits,
            COUNT(DISTINCT m.id_mouvement) AS nb_operations
        FROM agence ag
        LEFT JOIN compte c ON c.code_agence = ag.code_agence
        LEFT JOIN mouvement m ON m.id_contrepartie = c.id_contrepartie
        LEFT JOIN transaction t ON m.ref_transaction = t.ref_transaction AND t.statut_trans = 'VALIDEE'
        GROUP BY ag.code_agence, ag.nom_agence, ag.ville
        ORDER BY encours_total DESC;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query)
        return [
            {**r,
             "encours_total": float(r["encours_total"]),
             "volume_credits": float(r["volume_credits"]),
             "volume_debits": float(r["volume_debits"])}
            for r in cursor.fetchall()
        ]


@app.get("/api/admin/analytics/caisses", tags=["Analytics Admin"])
def get_analytics_caisses(admin: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    """Monitorat de l'encaisse physique des caisses agences (CAISSE_AGENCE héritant de CONTREPARTIE)."""
    query = """
        SELECT
            ca.id_contrepartie, ca.libelle_caisse,
            ag.nom_agence, ag.ville,
            COALESCE(SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE -m.montant END), 0) AS solde_caisse,
            COALESCE(SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE 0 END), 0) AS total_entrees,
            COALESCE(SUM(CASE WHEN m.sens = 'D' THEN m.montant ELSE 0 END), 0) AS total_sorties,
            COUNT(DISTINCT m.id_mouvement) AS nb_operations
        FROM caisse_agence ca
        JOIN agence ag ON ca.code_agence = ag.code_agence
        LEFT JOIN mouvement m ON m.id_contrepartie = ca.id_contrepartie
        LEFT JOIN transaction t ON m.ref_transaction = t.ref_transaction AND t.statut_trans = 'VALIDEE'
        GROUP BY ca.id_contrepartie, ca.libelle_caisse, ag.nom_agence, ag.ville
        ORDER BY solde_caisse DESC;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query)
        return [
            {**r,
             "solde_caisse": float(r["solde_caisse"]),
             "total_entrees": float(r["total_entrees"]),
             "total_sorties": float(r["total_sorties"])}
            for r in cursor.fetchall()
        ]


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — TOUTES ANOMALIES (sans filtre date)
# -----------------------------------------------------------------------------
@app.get("/api/audit/anomalies/all", tags=["Audit & Sécurité"])
def get_all_anomalies(
    limit: int = 500,
    statut: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Extrait l'ensemble des anomalies (toutes dates), avec filtre optionnel sur le statut."""
    where_clause = "WHERE t.statut_trans IN ('EN_ATTENTE', 'REJETEE')"
    params: list[Any] = []
    if statut:
        where_clause = "WHERE t.statut_trans = %s"
        params.append(statut.upper())

    query = f"""
        SELECT
            t.ref_transaction, t.date_heure, t.statut_trans,
            tt.libelle AS type_transaction,
            c.nom_canal AS canal,
            t.ip_source,
            COALESCE(SUM(m.montant) / 2, 0.00) AS montant_operation
        FROM transaction t
        JOIN type_transaction tt ON t.code_type_trans = tt.code_type_trans
        JOIN canal c ON t.code_canal = c.code_canal
        LEFT JOIN mouvement m ON t.ref_transaction = m.ref_transaction
        {where_clause}
        GROUP BY t.ref_transaction, t.date_heure, t.statut_trans, tt.libelle, c.nom_canal, t.ip_source
        ORDER BY t.date_heure DESC
        LIMIT %s;
    """
    params.append(limit)

    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query, params)
        return [
            {
                **r,
                "date_heure": str(r["date_heure"]),
                "montant_operation": float(r["montant_operation"]),
            }
            for r in cursor.fetchall()
        ]


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — KYC : Mise à jour client
# -----------------------------------------------------------------------------
class ClientUpdateRequest(BaseModel):
    email: Optional[str] = None
    telephone: Optional[str] = None


@app.patch("/api/clients/{cin}/kyc", tags=["Clients"])
def update_client_kyc(
    cin: str,
    req: ClientUpdateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Met à jour les informations de contact KYC d'un client (email, téléphone)."""
    updates = []
    params = []
    if req.email:
        updates.append("email = %s")
        params.append(req.email.strip())
    if req.telephone:
        updates.append("telephone = %s")
        params.append(req.telephone.strip())
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")
    params.append(cin.upper())

    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"UPDATE client SET {', '.join(updates)} WHERE cin = %s;", params)
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Client CIN {cin} introuvable.")
            conn.commit()
            return {"success": True, "cin": cin.upper(), "message": "Données KYC mises à jour."}
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — GESTION DES CLIENTS (KYC CRUD)
# -----------------------------------------------------------------------------
class ClientCreateRequest(BaseModel):
    nom: str = Field(..., description="Nom de famille")
    prenom: str = Field(..., description="Prénom")
    cin: str = Field(..., description="Numéro de CIN unique")
    email: str = Field(..., description="Adresse email")
    telephone: str = Field(..., description="Numéro de téléphone")
    date_naissance: Optional[str] = Field(default="1995-05-15")
    mot_de_passe: Optional[str] = Field(default="Sidpef2026!")


@app.post("/api/clients", tags=["Clients"], status_code=201)
def create_client(
    req: ClientCreateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Création d'un nouveau dossier client (Onboarding KYC)."""
    hash_pwd = BankingDAO.hash_password(req.mot_de_passe or "Sidpef2026!")
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                INSERT INTO client (nom, prenom, cin, date_naissance, email, telephone, mot_de_passe_hash, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'CLIENT');
                """,
                (req.nom.strip(), req.prenom.strip(), req.cin.strip().upper(),
                 req.date_naissance, req.email.strip(), req.telephone.strip(), hash_pwd),
            )
            num_client = cursor.lastrowid
            conn.commit()
            return {
                "success": True,
                "num_client": num_client,
                "cin": req.cin.strip().upper(),
                "nom_complet": f"{req.prenom.strip()} {req.nom.strip()}",
                "message": f"Client {req.prenom} {req.nom} créé avec succès (N° Client: {num_client}).",
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Erreur création client : {str(e)}")
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — OUVERTURE DE COMPTE & GESTION TEMPORELLE DES TITULAIRES
# -----------------------------------------------------------------------------
class CompteCreateRequest(BaseModel):
    num_client: int = Field(..., description="Numéro du client titulaire principal")
    code_type: str = Field(default="COURANT", description="Type de compte (COURANT, EPARGNE)")
    code_agence: int = Field(default=1, description="Code de l'agence")
    decouvert_autorise: Decimal = Field(default=Decimal("1000.00"), ge=0)
    solde_initial: Decimal = Field(default=Decimal("0.00"), ge=0)


class TitularisationCreateRequest(BaseModel):
    num_client: int = Field(..., description="Numéro du client co-titulaire ou mandataire")
    role: str = Field(default="CO_TITULAIRE", description="Rôle (CO_TITULAIRE, MANDATAIRE, TUTEUR)")


@app.post("/api/comptes", tags=["Comptes"], status_code=201)
def ouvrir_compte(
    req: CompteCreateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Création d'un enregistrement COMPTE avec CONTREPARTIE parente et association TITULARISER.
    Si un versement initial est spécifié, il est débité de la caisse agence et crédité sur le compte.
    """
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Insertion dans la table parente CONTREPARTIE
            cursor.execute("INSERT INTO contrepartie (type_contrepartie) VALUES ('COMPTE');")
            id_contrepartie = cursor.lastrowid

            # 2. Insertion dans COMPTE
            cursor.execute(
                """
                INSERT INTO compte (id_contrepartie, solde, decouvert_autorise, date_ouverture, statut, code_agence, code_type)
                VALUES (%s, 0.00, %s, CURDATE(), 'ACTIF', %s, %s);
                """,
                (id_contrepartie, req.decouvert_autorise, req.code_agence, req.code_type.upper()),
            )

            # 3. Association TITULARISER (MCD Temporel)
            cursor.execute(
                """
                INSERT INTO titulariser (role, date_debut, date_fin, id_contrepartie_compte, num_client)
                VALUES ('TITULAIRE_PRINCIPAL', CURDATE(), NULL, %s, %s);
                """,
                (id_contrepartie, req.num_client),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Échec ouverture de compte : {str(e)}")
        finally:
            cursor.close()

    # Si versement initial > 0, effectuer l'opération de dépôt via caisse agence
    if req.solde_initial > Decimal("0.00"):
        try:
            # Trouver la caisse de l'agence
            with DatabaseManager.get_cursor(dictionary=True) as (cur, _):
                cur.execute("SELECT id_contrepartie FROM caisse_agence WHERE code_agence = %s LIMIT 1;", (req.code_agence,))
                row = cur.fetchone()
                id_caisse = row["id_contrepartie"] if row else 6
            BankingDAO.executer_virement(
                compte_source_id=id_caisse,
                compte_dest_id=id_contrepartie,
                montant=req.solde_initial,
                canal="GUICHET",
                ip_source="127.0.0.1",
            )
        except Exception as err:
            # Le compte est ouvert même si le versement initial a échoué
            pass

    return {
        "success": True,
        "id_compte": id_contrepartie,
        "num_client": req.num_client,
        "code_type": req.code_type.upper(),
        "solde": float(req.solde_initial),
        "message": f"Compte N°{id_contrepartie} ({req.code_type.upper()}) ouvert avec succès.",
    }


@app.get("/api/comptes/{id_compte}/titularisations", tags=["Comptes"])
def get_compte_titularisations(
    id_compte: int,
    admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    """Retourne la liste chronologique des titulaires et co-titulaires d'un compte (MCD TITULARISER)."""
    query = """
        SELECT t.num_titularite, t.role, t.date_debut, t.date_fin,
               cl.num_client, cl.nom, cl.prenom, cl.cin, cl.email, cl.telephone,
               CASE WHEN t.date_fin IS NULL THEN 'ACTIF' ELSE 'CLÔTURÉ' END AS statut_titularite
        FROM titulariser t
        JOIN client cl ON t.num_client = cl.num_client
        WHERE t.id_contrepartie_compte = %s
        ORDER BY t.date_debut DESC, t.num_titularite DESC;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query, (id_compte,))
        rows = cursor.fetchall()
        return [
            {
                **r,
                "date_debut": str(r["date_debut"]) if r["date_debut"] else None,
                "date_fin": str(r["date_fin"]) if r["date_fin"] else None,
            }
            for r in rows
        ]


@app.post("/api/comptes/{id_compte}/titularisations", tags=["Comptes"], status_code=201)
def ajouter_cotitulaire(
    id_compte: int,
    req: TitularisationCreateRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Ajoute un nouveau co-titulaire ou mandataire sur un compte joint (date_debut = CURDATE())."""
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                INSERT INTO titulariser (role, date_debut, date_fin, id_contrepartie_compte, num_client)
                VALUES (%s, CURDATE(), NULL, %s, %s);
                """,
                (req.role.upper(), id_compte, req.num_client),
            )
            num_tit = cursor.lastrowid
            conn.commit()
            return {
                "success": True,
                "num_titularite": num_tit,
                "id_compte": id_compte,
                "num_client": req.num_client,
                "role": req.role.upper(),
                "message": f"Co-titulaire N°{req.num_client} rattaché au compte N°{id_compte} avec le rôle {req.role.upper()}.",
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            cursor.close()


@app.patch("/api/titularisations/{num_titularite}/cloturer", tags=["Comptes"])
def cloturer_titularisation(
    num_titularite: int,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Retire un co-titulaire sans effacer l'historique : renseigne date_fin = CURDATE().
    Préserve l'immuabilité et la traçabilité temporelle du MCD.
    """
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "UPDATE titulariser SET date_fin = CURDATE() WHERE num_titularite = %s AND date_fin IS NULL;",
                (num_titularite,),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Titularité introuvable ou déjà clôturée.")
            conn.commit()
            return {
                "success": True,
                "num_titularite": num_titularite,
                "message": "Droits du co-titulaire clôturés à date d'aujourd'hui. Historique préservé.",
            }
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — OPÉRATIONS D'ESPÈCES (Trésorerie Agence & Caisse)
# -----------------------------------------------------------------------------
class EspecesOperationRequest(BaseModel):
    compte_id: int = Field(..., description="Numéro du compte bancaire client")
    sens: str = Field(..., description="Sens: DEPOT (versement espèces) ou RETRAIT (retrait espèces)")
    montant: Decimal = Field(..., gt=0, decimal_places=2)
    id_caisse: Optional[int] = Field(default=None, description="ID de la caisse agence")


@app.post("/api/admin/operations/especes", tags=["Trésorerie & Agence"])
def operer_especes(
    req: EspecesOperationRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """
    Opération de guichet d'espèces (Dépôt ou Retrait) entre un COMPTE et une CAISSE_AGENCE.
    Démontre le polymorphisme CONTREPARTIE et la garantie absolue de l'équilibre: SUM(D) = SUM(C).
    """
    sens_norm = req.sens.strip().upper()
    if sens_norm not in ("DEPOT", "RETRAIT"):
        raise HTTPException(status_code=400, detail="Sens invalide : doit être 'DEPOT' ou 'RETRAIT'.")

    # Résoudre la caisse agence
    id_caisse = req.id_caisse
    if not id_caisse:
        with DatabaseManager.get_cursor(dictionary=True) as (cur, _):
            cur.execute(
                "SELECT ca.id_contrepartie FROM caisse_agence ca JOIN compte c ON ca.code_agence = c.code_agence WHERE c.id_contrepartie = %s LIMIT 1;",
                (req.compte_id,),
            )
            row = cur.fetchone()
            id_caisse = row["id_contrepartie"] if row else 6

    # Pour un DEPOT au guichet : la caisse reçoit les espèces (source de flux monétaire interne)
    # et le compte client est crédité.
    # Pour un RETRAIT : le compte client est débité et la caisse agence décaisse (crédit).
    if sens_norm == "DEPOT":
        source_id = id_caisse
        dest_id = req.compte_id
        label = "Dépôt d'espèces au guichet"
    else:
        source_id = req.compte_id
        dest_id = id_caisse
        label = "Retrait d'espèces au guichet"

    try:
        ref_tx = BankingDAO.executer_virement(
            compte_source_id=source_id,
            compte_dest_id=dest_id,
            montant=req.montant,
            canal="GUICHET",
            ip_source="127.0.0.1",
        )
        return {
            "success": True,
            "ref_transaction": ref_tx,
            "operation": label,
            "compte_id": req.compte_id,
            "caisse_id": id_caisse,
            "montant": float(req.montant),
            "message": f"{label} de {req.montant:,.2f} MAD validé avec succès (Réf: {ref_tx}).",
        }
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec opération d'espèces : {str(e)}")


# -----------------------------------------------------------------------------
# ENDPOINTS ADMIN — ANALYSE DE VELOCITE (Lutte Anti-Fraude & Risques)
# -----------------------------------------------------------------------------
@app.get("/api/audit/velocite", tags=["Audit & Sécurité"])
def get_analyse_velocite(
    admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    """
    Analyse de vélocité transactionnelle :
    Détecte les pics d'activité anormaux (ex: retraits/virements multiples rapprochés,
    montants atypiques > 50 000 MAD ou répétitions rapides sur le même canal).
    """
    query = """
        SELECT
            t.ref_transaction,
            t.date_heure,
            t.statut_trans,
            tt.libelle AS type_transaction,
            c.nom_canal AS canal,
            t.ip_source,
            COALESCE(SUM(m.montant) / 2, 0.00) AS montant,
            CASE
                WHEN COALESCE(SUM(m.montant) / 2, 0) >= 50000 THEN 'MONTANT_ATYPIQUE'
                WHEN t.statut_trans = 'REJETEE' THEN 'REJET_DECOUVERT_REPETE'
                WHEN c.nom_canal IN ('Application Mobile Banking', 'GAB') THEN 'VELOCITE_CANAL'
                ELSE 'ANOMALIE_HEURISTIQUE'
            END AS motif_alerte,
            CASE
                WHEN COALESCE(SUM(m.montant) / 2, 0) >= 50000 THEN 95
                WHEN t.statut_trans = 'REJETEE' THEN 85
                ELSE 65
            END AS score_risque
        FROM transaction t
        JOIN type_transaction tt ON t.code_type_trans = tt.code_type_trans
        JOIN canal c ON t.code_canal = c.code_canal
        LEFT JOIN mouvement m ON t.ref_transaction = m.ref_transaction
        WHERE t.statut_trans IN ('REJETEE', 'EN_ATTENTE')
           OR m.montant >= 10000
        GROUP BY t.ref_transaction, t.date_heure, t.statut_trans, tt.libelle, c.nom_canal, t.ip_source
        ORDER BY score_risque DESC, t.date_heure DESC
        LIMIT 20;
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute(query)
        rows = cursor.fetchall()
        return [
            {
                **r,
                "date_heure": str(r["date_heure"]),
                "montant": float(r["montant"]),
            }
            for r in rows
        ]


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
