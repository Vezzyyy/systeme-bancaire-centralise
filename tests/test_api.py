"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : test_api.py
SPRINT 7 : TESTS AUTOMATISES DE L'API RESTFUL & AUTHENTIFICATION JWT
RESPONSABLE : Saad Joudali & Equipe
=============================================================================
Valide l'ensemble des routes RESTful, l'authentification JWT (OAuth2),
les contrôles de sécurité RBAC et la conformité des codes d'erreur HTTP.
=============================================================================
"""

import os
import sys

# Assure la résolution des modules depuis la racine du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_healthcheck():
    """Verifie la disponibilite du service et la liaison avec MySQL."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UP"
    assert data["database"] == "banque_centrale_db"


def test_login_client_success():
    """Verifie l'authentification JWT d'un client et la generation du jeton."""
    res = client.post("/api/auth/login", json={
        "username": "yassine.chaouri@banque.ma",
        "password": "Sidpef2026!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["cin"] == "BE123456"
    assert data["user"]["role"] == "CLIENT"


def test_login_admin_success():
    """Verifie l'authentification d'un administrateur avec privileges eleves."""
    res = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "AdminSidpef2026!"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "ADMIN"


def test_login_bad_credentials():
    """Verifie le rejet strict (HTTP 401) en cas de mot de passe invalide."""
    res = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "MauvaisMotDePasse"
    })
    assert res.status_code == 401


def test_auth_me():
    """Verifie la recuperation de la session active avec Bearer token."""
    login_res = client.post("/api/auth/login", json={
        "username": "BE123456",
        "password": "Sidpef2026!"
    })
    token = login_res.json()["access_token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["cin"] == "BE123456"


def test_get_clients():
    """Verifie la recuperation du repertoire des clients."""
    res = client.get("/api/clients")
    assert res.status_code == 200
    clients = res.json()
    assert len(clients) >= 5
    assert any(c["cin"] == "BE123456" for c in clients)


def test_get_client_profile():
    """Verifie la vue 360° d'un client."""
    res = client.get("/api/clients/BE123456")
    assert res.status_code == 200
    data = res.json()
    assert data["client"]["cin"] == "BE123456"
    assert len(data["comptes"]) >= 1


def test_cross_client_forbidden():
    """Verifie le verrouillage RBAC : un client ne peut consulter le dossier d'un tiers."""
    login_res = client.post("/api/auth/login", json={
        "username": "yassine.chaouri@banque.ma",
        "password": "Sidpef2026!"
    })
    token = login_res.json()["access_token"]
    # Tentative d'acces au profil de Saad Joudali (BK654321) avec le jeton de Yassine Chaouri
    res = client.get("/api/clients/BK654321", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_get_client_not_found():
    """Verifie le code 404 pour un client inexistant."""
    res = client.get("/api/clients/INEXISTANT")
    assert res.status_code == 404


def test_get_releve_compte():
    """Verifie l'extraction du releve de compte chronologique."""
    res = client.get("/api/comptes/1/releve")
    assert res.status_code == 200
    releve = res.json()
    assert isinstance(releve, list)
    if len(releve) > 0:
        assert "solde_cumule" in releve[0]


def test_virement_nominal():
    """Verifie l'execution reussie d'un virement nominal."""
    res = client.post("/api/virements", json={
        "compte_source_id": 1,
        "compte_dest_id": 2,
        "montant": 50.00,
        "canal": "WEB"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["ref_transaction"].startswith("TX-PY-")


def test_virement_decouvert_rejete():
    """Verifie le rejet strict (HTTP 400) en cas de depassement de decouvert."""
    res = client.post("/api/virements", json={
        "compte_source_id": 2,
        "compte_dest_id": 1,
        "montant": 999999.00,
        "canal": "WEB"
    })
    assert res.status_code == 400
    assert "Provision insuffisante" in res.json()["detail"]


def test_audit_trigger():
    """Verifie que le trigger MySQL bloque l'altération et retourne le status attendu."""
    res = client.post("/api/audit/test-trigger", json={
        "id_mouvement": 1,
        "nouveau_montant": 9999.00
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "TRIGGER_BLOCKED_SUCCESS"
    assert data["code_erreur_mysql"] == 1644


def test_beneficiaires_externes():
    """Verifie l'extraction du repertoire des beneficiaires externes (MCD CONTREPARTIE)."""
    res = client.get("/api/beneficiaires")
    assert res.status_code == 200
    bens = res.json()
    assert isinstance(bens, list)
    assert len(bens) >= 1
    assert any("iban" in b for b in bens)


def test_cartes_client():
    """Verifie la consultation des cartes bancaires associees au client."""
    res = client.get("/api/cartes/client/1")
    assert res.status_code == 200
    cartes = res.json()
    assert isinstance(cartes, list)
    if len(cartes) > 0:
        assert "statut_carte" in cartes[0]
        assert "plafond_paiement" in cartes[0]


def test_equilibre_comptable_partie_double():
    """Verifie l'equilibre comptable absolu de la banque (Sum Debits == Sum Credits, Solde Net == 0.00)."""
    admin_login = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "AdminSidpef2026!"
    })
    token = admin_login.json()["access_token"]
    res = client.get("/api/audit/equilibre-comptable", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["equilibre_valide"] is True
    assert data["solde_net"] == 0.00


def test_analyse_velocite_fraude():
    """Verifie l'analyse de velocite et la detection d'anomalies transactionnelles."""
    admin_login = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "AdminSidpef2026!"
    })
    token = admin_login.json()["access_token"]
    res = client.get("/api/audit/velocite", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_titularisations_compte():
    """Verifie l'historique temporel des titulaires d'un compte (MCD TITULARISER)."""
    admin_login = client.post("/api/auth/login", json={
        "username": "admin@sidpef.ma",
        "password": "AdminSidpef2026!"
    })
    token = admin_login.json()["access_token"]
    res = client.get("/api/comptes/1/titularisations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    tits = res.json()
    assert isinstance(tits, list)
    assert len(tits) >= 1
    assert "role" in tits[0]


if __name__ == "__main__":
    print("Execution des tests API FastAPI & Securite JWT...")
    test_healthcheck()
    print("  [OK] Healthcheck")
    test_login_client_success()
    print("  [OK] Login Client JWT (200)")
    test_login_admin_success()
    print("  [OK] Login Admin JWT (200)")
    test_login_bad_credentials()
    print("  [OK] Login Bad Credentials Rejete (401)")
    test_auth_me()
    print("  [OK] Session Active /api/auth/me (200)")
    test_get_clients()
    print("  [OK] Get Clients")
    test_get_client_profile()
    print("  [OK] Get Client Profile 360")
    test_cross_client_forbidden()
    print("  [OK] Verrouillage Cross-Client RBAC (403)")
    test_get_client_not_found()
    print("  [OK] Get Client Not Found (404)")
    test_get_releve_compte()
    print("  [OK] Get Releve Compte")
    test_virement_nominal()
    print("  [OK] Virement Nominal (200)")
    test_virement_decouvert_rejete()
    print("  [OK] Virement Découvert Rejeté (400)")
    test_audit_trigger()
    print("  [OK] Audit Trigger Blocking (1644)")
    test_beneficiaires_externes()
    print("  [OK] Bénéficiaires Externes (CONTREPARTIE)")
    test_cartes_client()
    print("  [OK] Moyens de Paiement & Cartes")
    test_equilibre_comptable_partie_double()
    print("  [OK] Équilibre Comptable Partie Double (0.00 MAD)")
    test_analyse_velocite_fraude()
    print("  [OK] Analyse de Vélocité & Risques")
    test_titularisations_compte()
    print("  [OK] Historique Temporel des Titularités")
    print("\nTOUS LES TESTS API & SECURITE ONT REUSSI AVEC SUCCES (18/18) !")
