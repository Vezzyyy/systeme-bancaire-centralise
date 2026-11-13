"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
FICHIER : test_api.py
SPRINT 6 : TESTS AUTOMATISES DE L'API FASTAPI
RESPONSABLE : Saad Joudali
=============================================================================
Valide l'ensemble des routes RESTful, la conformite des reponses et
la gestion des codes HTTP d'erreur bancaires (400, 404, 500).
=============================================================================
"""

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


def test_get_clients():
    """Verifie la recuperation de la liste des clients."""
    res = client.get("/api/clients")
    assert res.status_code == 200
    clients = res.json()
    assert len(clients) >= 5
    assert any(c["cin"] == "BE123456" for c in clients)


def test_get_client_profile():
    """Verifie la vue 360° d'un client existant."""
    res = client.get("/api/clients/BE123456")
    assert res.status_code == 200
    data = res.json()
    assert data["client"]["cin"] == "BE123456"
    assert len(data["comptes"]) >= 1


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


if __name__ == "__main__":
    print("Execution des tests API FastAPI...")
    test_healthcheck()
    print("  [OK] Healthcheck")
    test_get_clients()
    print("  [OK] Get Clients")
    test_get_client_profile()
    print("  [OK] Get Client Profile 360")
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
    print("\nTOUS LES TESTS API ONT REUSSI AVEC SUCCES (8/8) !")
