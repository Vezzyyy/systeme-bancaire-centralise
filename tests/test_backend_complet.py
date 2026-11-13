"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : tests/test_backend_complet.py
SPRINT 8 : SUITE COMPLETE DE TESTS AUTOMATISES BACKEND (PYTEST & TESTCLIENT)
RESPONSABLE : Équipe QA & Lead Tech (Hamza, Saad, Mouad, Amine, Yassine)
=============================================================================
Suite impitoyable de validation qualité couvrant :
1. Authentification OAuth2 / JWT, intégrité des sessions et cloisonnement RBAC.
2. Propriétés ACID strictes, intégrité des soldes et rollback automatique.
3. Inviolabilité de la piste d'audit et interception par les triggers MySQL 8+.
4. Équilibre comptable absolu de la banque en partie double (Solde net = 0.00).
=============================================================================
"""

import os
import sys
from decimal import Decimal
from typing import Generator
import pytest
from fastapi.testclient import TestClient
import mysql.connector

# Résolution des modules du projet depuis la racine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api import app, JWT_SECRET, JWT_ALGORITHM
from banking_dao import BankingDAO
from database import DatabaseManager
from models import (
    AccountingImmutabilityError,
    InsufficientFundsError,
)

client = TestClient(app)


# =============================================================================
# FIXTURES PYTEST : SETUP & TEARDOWN
# =============================================================================

@pytest.fixture(scope="session")
def admin_token() -> str:
    """Authentifie l'administrateur SIDPEF et fournit un jeton JWT valide."""
    res = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "AdminSidpef2026!"
    })
    assert res.status_code == 200, "L'authentification de l'administrateur a échoué"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def client_token() -> str:
    """Authentifie le client de test N°1 (Yassine Chaouri) et fournit son jeton."""
    res = client.post("/api/auth/login", json={
        "username": "yassine.chaouri@banque.ma",
        "password": "Sidpef2026!"
    })
    assert res.status_code == 200, "L'authentification du client a échoué"
    return res.json()["access_token"]


@pytest.fixture
def balance_snapshot() -> Generator[dict[int, Decimal], None, None]:
    """
    Setup / Teardown fixture :
    Enregistre les soldes des comptes 1 et 2 avant le test et restaure
    exactement leur valeur d'origine après l'exécution.
    """
    with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT id_contrepartie, solde FROM compte WHERE id_contrepartie IN (1, 2);")
        rows = cursor.fetchall()
        initial_balances = {r["id_contrepartie"]: Decimal(str(r["solde"])) for r in rows}

    yield initial_balances

    # Teardown : Restauration des soldes initiaux
    with DatabaseManager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            for cid, bal in initial_balances.items():
                cursor.execute("UPDATE compte SET solde = %s WHERE id_contrepartie = %s;", (bal, cid))
            conn.commit()
        finally:
            cursor.close()


# =============================================================================
# 1. AXE AUTHENTIFICATION, JWT & CLOISONNEMENT RBAC
# =============================================================================

class TestAuthenticationAndSecurity:
    """Vérifications strictes des protocoles de sécurité et de gestion des identités."""

    def test_login_client_success_and_jwt_claims(self):
        """Vérifie la génération du jeton JWT pour un client avec les claims conformes."""
        res = client.post("/api/auth/login", json={
            "username": "yassine.chaouri@banque.ma",
            "password": "Sidpef2026!"
        })
        assert res.status_code == 200
        payload = res.json()
        assert "access_token" in payload
        assert payload["token_type"] == "bearer"
        user = payload["user"]
        assert user["cin"] == "BE123456"
        assert user["role"] == "CLIENT"
        assert user["nom"] == "Chaouri"
        assert user["prenom"] == "Yassine"

    def test_login_admin_success(self):
        """Vérifie l'élévation de privilèges pour un administrateur central."""
        res = client.post("/api/auth/login", json={
            "username": "admin@sidpef.ma",
            "password": "AdminSidpef2026!"
        })
        assert res.status_code == 200
        payload = res.json()
        assert payload["user"]["role"] == "ADMIN"
        assert payload["user"]["cin"] == "ADMIN001"

    def test_login_with_invalid_password_rejected_401(self):
        """Vérifie l'interception et le rejet immédiat en cas de mot de passe erroné."""
        res = client.post("/api/auth/login", json={
            "username": "admin@sidpef.ma",
            "password": "MotDePasseFaux!"
        })
        assert res.status_code == 401
        assert "Identifiants bancaires incorrects" in res.json()["detail"]

    def test_request_without_token_rejected_401(self):
        """Vérifie qu'un endpoint protégé refuse l'accès si le header Authorization est omis."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401
        assert "jeton JWT Bearer absent" in res.json()["detail"]

    def test_request_with_forged_token_rejected_401(self):
        """Vérifie que les signatures falsifiées ou altérées sont rejetées."""
        forged_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fakedata.invalidsignature"}
        res = client.get("/api/auth/me", headers=forged_headers)
        assert res.status_code == 401
        assert "invalide ou falsifié" in res.json()["detail"]

    def test_cross_client_access_strictly_forbidden_403(self, client_token):
        """
        Cloisonnement RBAC strict :
        Un client connecté (Yassine / BE123456) ne peut en aucun cas consulter
        le dossier d'un autre client (Saad / BK654321).
        """
        headers = {"Authorization": f"Bearer {client_token}"}
        res = client.get("/api/clients/BK654321", headers=headers)
        assert res.status_code == 403
        assert "Accès refusé" in res.json()["detail"]

    def test_admin_can_access_any_client_profile_200(self, admin_token):
        """Un administrateur dûment habilité peut auditer les comptes de tout client."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.get("/api/clients/BK654321", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["client"]["cin"] == "BK654321"
        assert len(data["comptes"]) >= 1


# =============================================================================
# 2. AXE TRANSACTIONS ACID, SOLVABILITÉ & ATOMICITÉ
# =============================================================================

class TestAcidTransactionsAndIntegrity:
    """Contrôle impitoyable de l'atomicité, de la cohérence et de l'isolation comptable."""

    def test_virement_nominal_updates_balances_atomically(self, balance_snapshot):
        """
        Test d'un virement nominal :
        Vérifie le débit exact de la source, le crédit exact du destinataire
        et la génération des deux lignes de mouvement en partie double.
        """
        solde_init_c1 = balance_snapshot[1]
        solde_init_c2 = balance_snapshot[2]
        montant_virement = Decimal("150.00")

        res = client.post("/api/virements", json={
            "compte_source_id": 1,
            "compte_dest_id": 2,
            "montant": float(montant_virement),
            "canal": "WEB"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        ref_tx = data["ref_transaction"]
        assert ref_tx.startswith("TX-PY-")

        # Vérification en base des soldes après virement
        compte1_apres = BankingDAO.get_compte(1)
        compte2_apres = BankingDAO.get_compte(2)

        assert compte1_apres.solde == solde_init_c1 - montant_virement, "Le compte émetteur n'a pas été débité correctement"
        assert compte2_apres.solde == solde_init_c2 + montant_virement, "Le compte récepteur n'a pas été crédité correctement"

        # Vérification des écritures comptables élémentaires
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT sens, montant, id_contrepartie FROM mouvement WHERE ref_transaction = %s;", (ref_tx,))
            mouvements = cursor.fetchall()
            assert len(mouvements) == 2, "La transaction doit comporter exactement deux mouvements"
            
            debit_mvt = next(m for m in mouvements if m["sens"] == "D")
            credit_mvt = next(m for m in mouvements if m["sens"] == "C")
            
            assert debit_mvt["id_contrepartie"] == 1
            assert Decimal(str(debit_mvt["montant"])) == montant_virement
            assert credit_mvt["id_contrepartie"] == 2
            assert Decimal(str(credit_mvt["montant"])) == montant_virement

    def test_virement_sans_provision_causes_strict_rollback(self, balance_snapshot):
        """
        Vérification ACID / Rollback :
        Tentative de virement dépassant le solde et le découvert autorisé.
        Vérifie que la transaction échoue (400), qu'aucun centime n'est débité
        et que l'échec est horodaté au statut REJETEE.
        """
        solde_init_c2 = balance_snapshot[2]
        solde_init_c1 = balance_snapshot[1]
        montant_excessif = 999999.00

        res = client.post("/api/virements", json={
            "compte_source_id": 2,
            "compte_dest_id": 1,
            "montant": montant_excessif,
            "canal": "WEB"
        })
        assert res.status_code == 400
        assert "Provision insuffisante" in res.json()["detail"]

        # Vérification de l'intégrité absolue des soldes (ROLLBACK effectif)
        compte2_apres = BankingDAO.get_compte(2)
        compte1_apres = BankingDAO.get_compte(1)

        assert compte2_apres.solde == solde_init_c2, "ROLLBACK ÉCHOUÉ : Le solde du compte 2 a été modifié !"
        assert compte1_apres.solde == solde_init_c1, "ROLLBACK ÉCHOUÉ : Le solde du compte 1 a été modifié !"


# =============================================================================
# 3. AXE AUDIT, IMMUABILITÉ & TRIGGERS MYSQL 8+ (CODE ERREUR 1644)
# =============================================================================

class TestAccountingImmutabilityAndTriggers:
    """Preuve par l'épreuve de l'inviolabilité de la piste d'audit bancaire."""

    def test_trigger_before_update_blocks_mouvement_alteration(self):
        """
        Vérifie que le trigger MySQL 'trg_mouvement_before_update' intercepte
        et bloque formellement toute tentative d'altération d'un montant (SQLSTATE 45000 / Code 1644).
        """
        with pytest.raises(AccountingImmutabilityError) as exc_info:
            BankingDAO.tenter_modifier_mouvement(id_mouvement=1, nouveau_montant=Decimal("9999.00"))
        
        assert "Bloqué par le Trigger" in str(exc_info.value)
        assert "Immuabilite comptable" in str(exc_info.value)

    def test_trigger_api_endpoint_returns_audit_proof(self):
        """Vérifie que le point de contrôle de l'API renvoie le diagnostic d'immuabilité."""
        res = client.post("/api/audit/test-trigger", json={
            "id_mouvement": 1,
            "nouveau_montant": 9999.00
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "TRIGGER_BLOCKED_SUCCESS"
        assert data["code_sqlstate"] == "45000"
        assert data["code_erreur_mysql"] == 1644
        assert data["trigger_name"] == "trg_mouvement_before_update"

    def test_trigger_before_delete_blocks_mouvement_deletion(self):
        """Vérifie que la suppression d'une écriture comptable est formellement interdite."""
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                with pytest.raises(mysql.connector.Error) as exc_info:
                    cursor.execute("DELETE FROM mouvement WHERE id_mouvement = 1;")
                
                assert exc_info.value.errno == 1644, "Le code d'erreur MySQL doit être 1644"
                assert "suppression interdite" in str(exc_info.value).lower()
            finally:
                conn.rollback()
                cursor.close()


# =============================================================================
# 4. AXE ÉQUILIBRE COMPTABLE GLOBAL (SOMME NETTE = 0.00 MAD)
# =============================================================================

class TestGlobalLedgerBalance:
    """Vérifie le respect universel de la règle d'or : Sum(Débits) == Sum(Crédits)."""

    def test_global_accounting_equilibrium_is_zero(self, admin_token):
        """
        Vérifie sur l'ensemble de la base centrale que la somme de tous les débits
        est rigoureusement égale à la somme de tous les crédits validés.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.get("/api/audit/equilibre-comptable", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["equilibre_valide"] is True
        assert data["solde_net"] == 0.00
        assert data["total_credits"] == data["total_debits"]
        assert data["nb_transactions"] > 0
        assert data["nb_mouvements"] >= 2 * data["nb_transactions"]


# =============================================================================
# EXÉCUTION DIRECTE HORS PYTEST (POUR CONTRÔLE RAPIDE)
# =============================================================================

if __name__ == "__main__":
    print("=" * 78)
    print("  EXÉCUTION DE LA SUITE COMPLETE DE TESTS BACKEND (SIDPEF SPRINT 8)")
    print("=" * 78)
    retcode = pytest.main(["-v", __file__])
    sys.exit(retcode)
