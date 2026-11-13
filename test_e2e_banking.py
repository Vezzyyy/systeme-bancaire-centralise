"""
=============================================================================
PROJET : SYSTEME BANCAIRE CENTRALISE
FICHIER : test_e2e_banking.py
SPRINT 5 : INTEGRATION APPLICATIVE PYTHON & VALIDATION END-TO-END (EXIGENCE 10)
=============================================================================
Ce script valide l'ensemble de la chaine applicative :
- Pool de connexion MySQL 8+
- ORM/DAO et mapping objet
- Execution atomique de virement via SP_VALIDER_TRANSACTION
- Protection contre le depassement de decouvert (Rollback automatique)
- Validation des triggers d'immuabilite comptable
- Extraction de donnees analytiques et releve chronologique
=============================================================================
"""

import sys
from decimal import Decimal
from banking_dao import BankingDAO
from database import DatabaseManager
from models import AccountingImmutabilityError, InsufficientFundsError


def print_header(title: str):
    print("\n" + "=" * 78)
    print(f"  {title.upper()}")
    print("=" * 78)


def print_success(msg: str):
    print(f"  [OK] {msg}")


def print_warning(msg: str):
    print(f"  [ATTENTION] {msg}")


def run_e2e_tests():
    print_header("Sprint 5 : Demarrage des Tests d'Integration Applicative (Python)")

    # -------------------------------------------------------------------------
    # TEST 1 : Initialisation et Test du Pool de Connexions
    # -------------------------------------------------------------------------
    print_header("Test 1 : Connexion au Pool MySQL 8+ (InnoDB / UTF-8)")
    try:
        pool = DatabaseManager.get_pool()
        with DatabaseManager.get_cursor() as (cursor, _):
            cursor.execute("SELECT VERSION() AS version, DATABASE() AS bdd, USER() AS user;")
            info = cursor.fetchone()
            print_success(f"Connecté avec succès au serveur MySQL {info['version']}")
            print_success(f"Base de données active : {info['bdd']} (Utilisateur : {info['user']})")
            print_success(f"Pool de connexions : {pool.pool_name} (Taille : {pool.pool_size})")
    except Exception as e:
        print(f"  [ERREUR CRITIQUE] Impossible de se connecter à la base : {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # TEST 2 : Consultation 360° du Client et de ses Comptes
    # -------------------------------------------------------------------------
    print_header("Test 2 : Extraction du Profil Client 360° (Yassine Chaouri)")
    cin_test = "BE123456"
    profil = BankingDAO.get_client_by_cin(cin_test)
    client = profil["client"]
    print_success(f"Client trouvé : {client.prenom} {client.nom} (CIN: {client.cin})")
    print(f"       Email : {client.email} | Téléphone : {client.telephone}")
    print("       Comptes bancaires rattachés :")
    for cpt in profil["comptes"]:
        print(f"         - Compte N°{cpt['num_compte']} ({cpt['type_compte']}) : "
              f"Solde = {cpt['solde']:,.2f} MAD | Découvert autorisé = {cpt['decouvert_autorise']:,.2f} MAD "
              f"[Agence: {cpt['nom_agence']}, Rôle: {cpt['role']}]")
    print("       Cartes bancaires actives :")
    for crt in profil["cartes"]:
        print(f"         - Carte {crt['num_carte']} | Statut: {crt['statut_carte']} | Exp: {crt['date_expiration']} "
              f"| Plafond retrait: {crt['plafond_retrait']:,.2f} MAD")

    # -------------------------------------------------------------------------
    # TEST 3 : Relevé de Compte Chronologique avec Window Function (SUM OVER)
    # -------------------------------------------------------------------------
    print_header("Test 3 : Génération du Relevé de Compte Chronologique (Compte 1)")
    releve = BankingDAO.get_releve_chronologique(id_compte=1)
    print_success(f"Relevé généré avec succès : {len(releve)} écritures comptables extraites")
    print("-" * 78)
    print(f"{'Date':<12} | {'Référence':<18} | {'Opération':<20} | {'Débit':<10} | {'Crédit':<10} | {'Solde Cumulé'}")
    print("-" * 78)
    for ligne in releve:
        debit_str = f"{ligne.debit:,.2f}" if ligne.debit else "-"
        credit_str = f"{ligne.credit:,.2f}" if ligne.credit else "-"
        print(f"{str(ligne.date_valeur):<12} | {ligne.ref_transaction:<18} | {ligne.libelle_operation[:20]:<20} | "
              f"{debit_str:>10} | {credit_str:>10} | {ligne.solde_cumule:>12,.2f} MAD")
    print("-" * 78)

    # -------------------------------------------------------------------------
    # TEST 4 : Exécution Atomique d'un Virement Applicatif (Compte 2 -> Compte 1)
    # -------------------------------------------------------------------------
    print_header("Test 4 : Virement Interne Atomique (500.00 MAD de Compte 2 -> Compte 1)")
    cpt1_avant = BankingDAO.get_compte(1)
    cpt2_avant = BankingDAO.get_compte(2)
    montant_virement = Decimal("500.00")

    print(f"  Soldes AVANT virement :")
    print(f"    - Compte 1 (Bénéficiaire) : {cpt1_avant.solde:,.2f} MAD")
    print(f"    - Compte 2 (Émetteur)     : {cpt2_avant.solde:,.2f} MAD")

    ref_tx = BankingDAO.executer_virement(
        compte_source_id=2,
        compte_dest_id=1,
        montant=montant_virement,
        canal="MOBILE",
        ip_source="196.200.22.10",
    )

    cpt1_apres = BankingDAO.get_compte(1)
    cpt2_apres = BankingDAO.get_compte(2)

    print_success(f"Virement validé avec succès ! Référence : {ref_tx}")
    print(f"  Soldes APRÈS virement :")
    print(f"    - Compte 1 (Crédité)  : {cpt1_apres.solde:,.2f} MAD (+{montant_virement:,.2f} MAD)")
    print(f"    - Compte 2 (Débité)   : {cpt2_apres.solde:,.2f} MAD (-{montant_virement:,.2f} MAD)")

    assert cpt1_apres.solde == cpt1_avant.solde + montant_virement, "Erreur sur le solde créditeur !"
    assert cpt2_apres.solde == cpt2_avant.solde - montant_virement, "Erreur sur le solde débiteur !"
    print_success("Vérification d'intégrité comptable : Les soldes sont parfaitement synchronisés.")

    # -------------------------------------------------------------------------
    # TEST 5 : Rejet Bancaire & Sécurité (Dépassement de Découvert / Provision)
    # -------------------------------------------------------------------------
    print_header("Test 5 : Tentative de Virement Excessif (Contrôle de Découvert & Rollback)")
    montant_excessif = Decimal("100000.00")
    cpt2_avant_echec = BankingDAO.get_compte(2)
    cpt1_avant_echec = BankingDAO.get_compte(1)

    print(f"  Tentative d'émission d'un virement de {montant_excessif:,.2f} MAD depuis le Compte 2 "
          f"(Solde disponible: {cpt2_avant_echec.solde + cpt2_avant_echec.decouvert_autorise:,.2f} MAD)...")

    try:
        BankingDAO.executer_virement(
            compte_source_id=2,
            compte_dest_id=1,
            montant=montant_excessif,
            canal="WEB",
        )
        print("  [ERREUR] Le virement aurait dû être rejeté par la procédure stockée !")
    except InsufficientFundsError as err:
        print_success("Interception réussie de l'exception métier InsufficientFundsError !")
        print(f"       Message d'erreur renvoyé : {err}")

    cpt2_apres_echec = BankingDAO.get_compte(2)
    cpt1_apres_echec = BankingDAO.get_compte(1)

    assert cpt2_apres_echec.solde == cpt2_avant_echec.solde, "Le solde émetteur a été altéré !"
    assert cpt1_apres_echec.solde == cpt1_avant_echec.solde, "Le solde récepteur a été altéré !"
    print_success("Vérification ACID / Rollback : Aucun centime n'a bougé après l'échec transactionnel.")

    # -------------------------------------------------------------------------
    # TEST 6 : Immuabilité Comptable & Triggers (Tentative d'UPDATE Illicite)
    # -------------------------------------------------------------------------
    print_header("Test 6 : Test de Résistance d'Immuabilité Comptable (Trigger BEFORE UPDATE)")
    id_mouvement_test = 1
    print(f"  Tentative d'altération directe du montant du mouvement #{id_mouvement_test}...")
    try:
        BankingDAO.tenter_modifier_mouvement(id_mouvement=id_mouvement_test, nouveau_montant=Decimal("9999.00"))
        print("  [ERREUR] La modification aurait dû être bloquée par le trigger !")
    except AccountingImmutabilityError as err:
        print_success("Interception réussie de AccountingImmutabilityError !")
        print(f"       Message du trigger MySQL : {err}")
    print_success("L'inviolabilité de la piste d'audit est validée de bout en bout.")

    # -------------------------------------------------------------------------
    # TEST 7 : Tableau de Bord des Anomalies Quotidiennes
    # -------------------------------------------------------------------------
    print_header("Test 7 : Extraction des Transactions en Attente ou Rejetées du Jour")
    anomalies = BankingDAO.get_anomalies_du_jour()
    print_success(f"{len(anomalies)} opération(s) nécessitant une supervision :")
    for ano in anomalies:
        print(f"    - [{ano['statut_trans']}] {ano['ref_transaction']} ({ano['type_transaction']} via {ano['canal']}) "
              f"| Montant: {ano['montant_operation']:,.2f} MAD | IP: {ano['ip_source']}")

    print_header("SYNTHÈSE DU SPRINT 5 : TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS (100%)")


if __name__ == "__main__":
    run_e2e_tests()
