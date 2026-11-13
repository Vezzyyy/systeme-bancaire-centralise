"""
Module d'accès aux données bancaires (Data Access Object / ORM).
Gère l'interaction avec MySQL, les procédures stockées et l'intégrité transactionnelle.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid
import bcrypt
import mysql.connector
from database import DatabaseManager
from models import (
    AccountNotFoundError,
    AccountingImmutabilityError,
    BankingException,
    Client,
    Compte,
    InsufficientFundsError,
    ReleveLigne,
)


class BankingDAO:
    """Classe d'accès aux opérations bancaires et analytiques."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe en clair par rapport à son empreinte bcrypt."""
        if not hashed_password or not plain_password:
            return False
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Génère une empreinte bcrypt sécurisée avec sel aléatoire."""
        salt = bcrypt.gensalt(10)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def authenticate_user(login: str, password: str) -> Optional[dict]:
        """
        Authentifie un utilisateur (client ou administrateur) par email ou CIN.
        Retourne le dictionnaire du profil sans le hash si valide, None sinon.
        """
        query = """
            SELECT num_client, nom, prenom, cin, date_naissance, email, telephone,
                   role, mot_de_passe_hash
            FROM client
            WHERE email = %s OR cin = %s;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (login.strip(), login.strip().upper()))
            row = cursor.fetchone()
            if not row or not row.get("mot_de_passe_hash"):
                return None
            if not BankingDAO.verify_password(password, row["mot_de_passe_hash"]):
                return None
            return {
                "num_client": row["num_client"],
                "nom": row["nom"],
                "prenom": row["prenom"],
                "cin": row["cin"],
                "date_naissance": str(row["date_naissance"]) if row["date_naissance"] else None,
                "email": row["email"],
                "telephone": row["telephone"],
                "role": row.get("role", "CLIENT"),
            }

    @staticmethod
    def get_user_by_cin(cin: str) -> Optional[dict]:
        """Retourne les informations d'un utilisateur par son CIN."""
        query = """
            SELECT num_client, nom, prenom, cin, date_naissance, email, telephone, role
            FROM client
            WHERE cin = %s;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (cin.strip().upper(),))
            row = cursor.fetchone()
            if not row:
                return None
            if row.get("date_naissance"):
                row["date_naissance"] = str(row["date_naissance"])
            return row

    @staticmethod
    def get_compte(id_compte: int) -> Compte:
        """Récupère les informations d'un compte bancaire par son identifiant."""
        query = """
            SELECT id_contrepartie, solde, decouvert_autorise, date_ouverture, 
                   statut, code_agence, code_type
            FROM compte
            WHERE id_contrepartie = %s;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (id_compte,))
            row = cursor.fetchone()
            if not row:
                raise AccountNotFoundError(f"Compte {id_compte} introuvable.")
            return Compte(
                id_compte=row["id_contrepartie"],
                solde=row["solde"],
                decouvert_autorise=row["decouvert_autorise"],
                date_ouverture=row["date_ouverture"],
                statut=row["statut"],
                code_agence=row["code_agence"],
                code_type=row["code_type"],
            )

    @staticmethod
    def get_client_by_cin(cin: str) -> dict:
        """Vue consolidée 360° d'un client, de ses comptes et cartes associées."""
        client_query = "SELECT * FROM client WHERE cin = %s;"
        comptes_query = """
            SELECT c.id_contrepartie AS num_compte, tc.libelle AS type_compte, 
                   c.solde, c.decouvert_autorise, ag.nom_agence, t.role
            FROM titulariser t
            JOIN compte c ON t.id_contrepartie_compte = c.id_contrepartie
            JOIN type_compte tc ON c.code_type = tc.code_type
            JOIN agence ag ON c.code_agence = ag.code_agence
            WHERE t.num_client = %s;
        """
        cartes_query = """
            SELECT num_carte, date_expiration, statut_carte, plafond_paiement, plafond_retrait
            FROM carte_bancaire
            WHERE num_client = %s;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(client_query, (cin,))
            client_row = cursor.fetchone()
            if not client_row:
                raise BankingException(f"Client avec CIN {cin} introuvable.")

            num_client = client_row["num_client"]
            cursor.execute(comptes_query, (num_client,))
            comptes = cursor.fetchall()

            cursor.execute(cartes_query, (num_client,))
            cartes = cursor.fetchall()

            return {
                "client": Client(
                    num_client=client_row["num_client"],
                    nom=client_row["nom"],
                    prenom=client_row["prenom"],
                    cin=client_row["cin"],
                    date_naissance=client_row["date_naissance"],
                    email=client_row["email"],
                    telephone=client_row["telephone"],
                    role=client_row.get("role", "CLIENT"),
                ),
                "comptes": comptes,
                "cartes": cartes,
            }

    @staticmethod
    def get_releve_chronologique(id_compte: int) -> list[ReleveLigne]:
        """
        Extrait le relevé de compte chronologique avec calcul dynamique du solde progressif
        en exploitant la fonction de fenêtrage analytique MySQL 8+ SUM() OVER.
        """
        query = """
            SELECT 
                m.id_mouvement,
                t.date_heure,
                m.date_valeur,
                t.ref_transaction,
                tt.libelle AS libelle_operation,
                cn.nom_canal AS canal,
                CASE WHEN m.sens = 'D' THEN m.montant ELSE NULL END AS debit,
                CASE WHEN m.sens = 'C' THEN m.montant ELSE NULL END AS credit,
                SUM(CASE WHEN m.sens = 'C' THEN m.montant ELSE -m.montant END) 
                    OVER (
                        PARTITION BY m.id_contrepartie 
                        ORDER BY m.id_mouvement ASC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS solde_progressif_mouvements
            FROM mouvement m
            JOIN transaction t ON m.ref_transaction = t.ref_transaction
            JOIN type_transaction tt ON t.code_type_trans = tt.code_type_trans
            JOIN canal cn ON t.code_canal = cn.code_canal
            WHERE m.id_contrepartie = %s
              AND t.statut_trans = 'VALIDEE'
            ORDER BY m.id_mouvement ASC;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (id_compte,))
            rows = cursor.fetchall()
            return [
                ReleveLigne(
                    id_mouvement=r["id_mouvement"],
                    date_heure=r["date_heure"],
                    date_valeur=r["date_valeur"],
                    ref_transaction=r["ref_transaction"],
                    libelle_operation=r["libelle_operation"],
                    canal=r["canal"],
                    debit=r["debit"],
                    credit=r["credit"],
                    solde_cumule=r["solde_progressif_mouvements"],
                )
                for r in rows
            ]

    @staticmethod
    def get_anomalies_du_jour() -> list[dict]:
        """Extrait les transactions en attente ou rejetées du jour."""
        query = """
            SELECT 
                t.ref_transaction,
                t.date_heure,
                t.statut_trans,
                tt.libelle AS type_transaction,
                c.nom_canal AS canal,
                t.ip_source,
                COALESCE(SUM(m.montant) / 2, 0.00) AS montant_operation
            FROM transaction t
            JOIN type_transaction tt ON t.code_type_trans = tt.code_type_trans
            JOIN canal c ON t.code_canal = c.code_canal
            LEFT JOIN mouvement m ON t.ref_transaction = m.ref_transaction
            WHERE t.statut_trans IN ('EN_ATTENTE', 'REJETEE')
              AND DATE(t.date_heure) = CURDATE()
            GROUP BY t.ref_transaction, t.date_heure, t.statut_trans, tt.libelle, c.nom_canal, t.ip_source
            ORDER BY t.date_heure DESC;
        """
        with DatabaseManager.get_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query)
            return cursor.fetchall()

    @staticmethod
    def executer_virement(
        compte_source_id: int,
        compte_dest_id: int,
        montant: Decimal,
        canal: str = "MOBILE",
        ip_source: str = "127.0.0.1",
    ) -> str:
        """
        Exécute un virement de bout en bout de façon atomique :
        1. Création de la transaction (EN_ATTENTE)
        2. Écriture des deux mouvements en partie double (D et C)
        3. Appel de la procédure stockée SP_VALIDER_TRANSACTION
        4. COMMIT / ROLLBACK strict et gestion des exceptions
        """
        if montant <= Decimal("0.00"):
            raise BankingException("Le montant du virement doit être strictement positif.")

        if compte_source_id == compte_dest_id:
            raise BankingException("Le compte source et le compte destinataire doivent être distincts.")

        # Référence unique de transaction
        ref_tx = f"TX-PY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # 1. Insertion de la transaction
                insert_tx_sql = """
                    INSERT INTO `transaction` (
                        ref_transaction, date_heure, statut_trans, ip_source, 
                        code_type_trans, code_canal
                    ) VALUES (%s, NOW(), 'EN_ATTENTE', %s, 'VIREMENT', %s);
                """
                cursor.execute(insert_tx_sql, (ref_tx, ip_source, canal))

                # 2. Insertion des deux mouvements en partie double
                insert_mv_sql = """
                    INSERT INTO `mouvement` (
                        sens, montant, date_valeur, devise, ref_transaction, id_contrepartie
                    ) VALUES (%s, %s, CURDATE(), 'MAD', %s, %s);
                """
                # Débit émetteur
                cursor.execute(insert_mv_sql, ("D", montant, ref_tx, compte_source_id))
                # Crédit récepteur
                cursor.execute(insert_mv_sql, ("C", montant, ref_tx, compte_dest_id))

                # 3. Validation comptable via la procédure stockée MySQL
                cursor.callproc("SP_VALIDER_TRANSACTION", (ref_tx,))

                # 4. Validation finale de la transaction
                conn.commit()
                return ref_tx

            except mysql.connector.Error as err:
                conn.rollback()
                err_msg = str(err)
                if "Provision insuffisante" in err_msg or "decouvert" in err_msg:
                    raise InsufficientFundsError(f"Rejet bancaire : {err_msg}") from err
                raise BankingException(f"Erreur SQL lors du virement : {err_msg}") from err
            except Exception as e:
                conn.rollback()
                raise BankingException(f"Échec inattendu du virement : {str(e)}") from e
            finally:
                cursor.close()

    @staticmethod
    def tenter_modifier_mouvement(id_mouvement: int, nouveau_montant: Decimal) -> None:
        """
        Méthode de test tentant une altération illégale d'un mouvement
        pour prouver l'interception par le trigger MySQL d'immuabilité.
        """
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE mouvement SET montant = %s WHERE id_mouvement = %s;",
                    (nouveau_montant, id_mouvement),
                )
                conn.commit()
            except mysql.connector.Error as err:
                conn.rollback()
                if "Immuabilite comptable" in str(err) or err.errno == 1644:
                    raise AccountingImmutabilityError(f"Bloqué par le Trigger : {err.msg}") from err
                raise
            finally:
                cursor.close()
