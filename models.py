"""
Modèles de données typés et hiérarchie d'exceptions métier.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


# =============================================================================
# EXCEPTIONS METIER BANCAIRES
# =============================================================================

class BankingException(Exception):
    """Exception de base pour les erreurs applicatives bancaires."""
    pass


class AccountNotFoundError(BankingException):
    """Le compte demande n'existe pas en base."""
    pass


class InsufficientFundsError(BankingException):
    """Le solde et le decouvert autorise sont insuffisants pour l'operation."""
    pass


class AccountingImmutabilityError(BankingException):
    """Tentative illicite de modification ou suppression d'une ecriture comptable."""
    pass


class InvalidTransactionStateError(BankingException):
    """La transaction n'est pas dans un etat permettant l'operation requise."""
    pass


# =============================================================================
# MODELES DE DONNEES (DATACLASSES)
# =============================================================================

@dataclass
class Client:
    num_client: int
    nom: str
    prenom: str
    cin: str
    date_naissance: Optional[date]
    email: Optional[str]
    telephone: Optional[str]
    role: str = "CLIENT"
    mot_de_passe_hash: Optional[str] = None


@dataclass
class Compte:
    id_compte: int
    solde: Decimal
    decouvert_autorise: Decimal
    date_ouverture: date
    statut: str
    code_agence: int
    code_type: str


@dataclass
class ReleveLigne:
    id_mouvement: int
    date_heure: datetime
    date_valeur: date
    ref_transaction: str
    libelle_operation: str
    canal: str
    debit: Optional[Decimal]
    credit: Optional[Decimal]
    solde_cumule: Decimal
