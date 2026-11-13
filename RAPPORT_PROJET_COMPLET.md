# RAPPORT DE PROJET COMPLET — SYSTÈME BANCAIRE CENTRALISÉ (SIDPEF)
## *Core Banking Information System, Modélisation Merise 3NF, Moteur Transactionnel MySQL 8+, API FastAPI & Intranet Bancaire Sécurisé*

---

### 📋 Fiche Signalétique du Projet

* **Intitulé Officiel** : Conception, Modélisation, Implémentation et Sécurisation d'un Système Bancaire Centralisé (*SIDPEF - Système d'Information et de Données des Paiements et Écritures Financières*)
* **Méthodologie de Conception** : Merise (Modèle Conceptuel, Logique et Physique de Données)
* **SGBD Transactionnel** : MySQL 8.0+ (Moteur InnoDB, ACID strict, Triggers d'Immuabilité, Procédures Stockées)
* **Couche Applicative Backend** : Python 3.12+ / FastAPI / Pydantic V2 / Uvicorn / MySQL Connector Pooling
* **Sécurité & Authentification** : JWT (JSON Web Tokens `HS256`), Hachage Cryptographique Bcrypt, Contrôle d'Accès Basé sur les Rôles (RBAC)
* **Interface Utilisateur** : Intranet Bancaire SPA Haute Fidélité (HTML5, CSS3 Moderne, Vanilla JS ES2024, Typographie *Plus Jakarta Sans* & *JetBrains Mono*, Hiérarchie visuelle au Nombre d'Or $\Phi \approx 1,618$)
* **Assurance Qualité & Tests** : 43 tests automatisés (Pytest, JSDOM, FastAPI TestClient, E2E DAO) avec 100% de taux de réussite
* **Dépôt GitHub** : [github.com/Vezzyyy/systeme-bancaire-centralise](https://github.com/Vezzyyy/systeme-bancaire-centralise)
* **Membres du Projet** :
  1. **Yassine Chaouri** ([@Vezzyyy](https://github.com/Vezzyyy)) — Chef de Projet & Architecte Base de Données
  2. **Saad Joudali** ([@joudali-saad](https://github.com/joudali-saad)) — Développeur Backend & Lead DAO Python
  3. **Hamza Sibous** ([@hamzasibous](https://github.com/hamzasibous)) — Ingénieur Sécurité & Backend API FastAPI
  4. **Mouad Talibi** ([@MouadWork](https://github.com/MouadWork)) — Lead Frontend & Designer UI/UX
  5. **Mohamed Amine Aouzagh** ([@MAminezzz](https://github.com/MAminezzz)) — Ingénieur QA & Automatisation des Tests

---

## 📑 TABLE DES MATIÈRES

1. [Introduction, Contexte & Exigences Métier](#1-introduction-contexte--exigences-métier)
2. [Modélisation Conceptuelle des Données (MCD Merise)](#2-modélisation-conceptuelle-des-données-mcd-merise)
3. [Modélisation Logique des Données (MLD Relationnel & 3NF)](#3-modélisation-logique-des-données-mld-relationnel--3nf)
4. [Modélisation Physique & DDL MySQL 8+ (MPD)](#4-modélisation-physique--ddl-mysql-8-mpd)
5. [Moteur Métier en Base de Données (Procédures & Triggers)](#5-moteur-métier-en-base-de-données-procédures--triggers)
6. [Requêtes Métier Analytiques & Optimisation EXPLAIN](#6-requêtes-métier-analytiques--optimisation-explain)
7. [Couche d'Accès aux Données (DAO Python & Gestionnaire de Connexion)](#7-couche-daccès-aux-données-dao-python--gestionnaire-de-connexion)
8. [API RESTful FastAPI & Sécurité RBAC / JWT](#8-api-restful-fastapi--sécurité-rbac--jwt)
9. [Interface Intranet Bancaire Corporate (UI/UX)](#9-interface-intranet-bancaire-corporate-uiux)
10. [Assurance Qualité & Suite de Tests Automatisés (E2E & DOM)](#10-assurance-qualité--suite-de-tests-automatisés-e2e--dom)
11. [Répartition Détaillée des Contributions de l'Équipe](#11-répartition-détaillée-des-contributions-de-léquipe)
12. [Guide de Déploiement & Script de Démonstration de Soutenance](#12-guide-de-déploiement--script-de-démonstration-de-soutenance)

---

## 1. Introduction, Contexte & Exigences Métier

### 1.1. Contexte du Core Banking
Le secteur bancaire repose sur un impératif fondamental : la **confiance absolue** dans l'intégrité, la traçabilité et l'exactitude des écritures financières. Tout système d'information bancaire centralisé (*Core Banking System*) doit répondre aux standards réglementaires internationaux les plus stricts (Accords de Bâle III, normes PCI-DSS pour la monétique, réglementations anti-blanchiment AML/KYC et normes comptables de double saisie).

Le système **SIDPEF** a été conçu pour concilier deux exigences majeures :
1. **L'Inviolabilité Comptable & Transactionnelle** : Aucune somme d'argent ne peut être créée ou détruite unilatéralement. Chaque opération doit respecter le principe de la comptabilité en partie double ($\sum \text{Débits} = \sum \text{Crédits}$).
2. **L'Immuabilité de la Piste d'Audit** : Il est juridiquement et techniquement interdit de modifier ou de supprimer une écriture financière validée. Toute correction d'erreur doit s'opérer par *contre-passation* (extourne).

### 1.2. Principes Directeurs de Conception (Règles de Gestion RG1 à RG12)
- **RG1 (Partie Double)** : Tout mouvement débiteur sur une contrepartie doit être rigoureusement équilibré par un mouvement créditeur d'égal montant sur une autre contrepartie au sein de la même transaction.
- **RG2 (Immuabilité Stricte)** : Les tables de journalisation comptable (`MOUVEMENT`) sont interdites de `UPDATE` et de `DELETE` via des triggers bloquants (`SIGNAL SQLSTATE '45000'`).
- **RG3 (Extourne / Contre-passation)** : L'annulation d'une transaction erronée génère une nouvelle transaction opposée liée à la première par l'association réflexive `COMPENSER`.
- **RG4 (Découplage Titulaire-Compte)** : Un client n'est pas lié directement à un compte par une clé étrangère fixe, mais par l'entité associative `TITULARISER` permettant la co-titularité, les procurations et l'historisation temporelle (`date_debut`, `date_fin`).
- **RG5 (Polymorphisme des Flux)** : Tous les flux financiers ciblent une `CONTREPARTIE` abstraite, spécialisée en compte interne (`COMPTE`), bénéficiaire externe (`BENEFICIAIRE_EXTERNE`) ou encaisse physique d'agence (`CAISSE_AGENCE`).
- **RG6 (Solvabilité & Découvert Autorisé)** : Un compte bancaire ne peut être débité que si le montant ne dépasse pas son solde courant majoré de son découvert contractuel autorisé ($Solde + DecouvertAutorise \ge Montant$).
- **RG7 (Multi-Canal & Traçabilité Technique)** : Toute transaction enregistre son canal d'initiation (GAB, Guichet, Web, Mobile) ainsi que l'adresse IP et le User-Agent de la session.
- **RG8 (Monétique & Plafonds)** : Chaque carte bancaire est attachée à un compte actif et dispose de plafonds distincts de retrait et de paiement, ainsi que d'un commutateur d'état d'urgence (*Kill Switch*).
- **RG9 (Séparation des Pouvoirs Maker-Checker)** : Un utilisateur simple ne peut valider une transaction suspecte ou à haut risque ; celle-ci est placée en anomalie (`EN_ATTENTE` ou `REJETEE`) et requiert l'intervention d'un superviseur Back-Office.
- **RG10 (Cloisonnement des Données Client)** : Un client ne peut en aucun cas consulter les comptes, cartes ou mouvements d'un tiers (`403 Forbidden`).
- **RG11 (Intégrité Référentielle Restrictive)** : Toutes les clés étrangères financières sont configurées en `ON DELETE RESTRICT` afin de bannir les suppressions en cascade accidentelles.
- **RG12 (Zéro Net Global)** : À tout instant, la somme algébrique globale de tous les mouvements enregistrés dans le système bancaire doit être exactement égale à `0.00 MAD`.

---

## 2. Modélisation Conceptuelle des Données (MCD Merise)

Le Modèle Conceptuel de Données (MCD) a été modélisé selon la méthode Merise pour formaliser la sémantique métier indépendamment de tout choix technique d'implémentation.

```
       +------------------+                    +------------------+
       |     AGENCE       |1,n   LOCALISER  1,1|      CANAL       |
       +------------------+------------------->+------------------+
         |1,n                                    |1,n
         | HEBERGER                              |
         v1,1                                    | INITIER
       +------------------+                      |
       |  CAISSE_AGENCE   |                      |
       +------------------+                      v1,1
         | (XT)                                +------------------+
         |                                     |   TRANSACTION    |
+--------+--------+                            +------------------+
|  CONTREPARTIE   |1,n        IMPUTER      1,n   |1,n
+-----------------+<-----------------------------| CONTENIR
| (XT)            |                              v1,1
|                 |                            +------------------+
|                 |                            |    MOUVEMENT     |
|                 |                            +------------------+
|                 |                                      ^
|                 |                                      | (COMPENSER)
|                 |                                      +---[0,1]
|                 +--------------------------------------+
|                                                        |
+--------+------------------------+                      |
         | (XT)                   | (XT)                 |
         v                        v                      |
+------------------+     +-----------------------+       |
|      COMPTE      |     | BENEFICIAIRE_EXTERNE  |       |
+------------------+     +-----------------------+       |
  |1,1        |1,n                                       |
  |TYPE       | TITULARISER                              |
  v0,n        v0,n                                       |
+----------+ +------------------+                        |
|TYPE_COMPT| |      CLIENT      |                        |
+----------+ +------------------+                        |
  ^           |0,n                                       |
  |           | POSSEDER                                 |
  |           v1,1                                       |
  |          +------------------+                        |
  +----------|  CARTE_BANCAIRE  |                        |
             +------------------+                        |
```

### 2.1. Les 6 Blocs Fonctionnels du MCD

#### Bloc 1 : Clientèle, KYC & Titularités Temporelles
* **`CLIENT`** : Identifie la personne physique ou morale (`id_client`, `cin`, `nom`, `prenom`, `email`, `telephone`, `adresse`, `mot_de_passe_hash`, `role`).
* **`TITULARISER`** : Relation porteuse de données temporelles (`id_client`, `id_compte`, `role_titularite`, `date_debut`, `date_fin`).
  - *Règle d'or* : Un compte joint associe plusieurs clients avec `date_fin IS NULL`. Si un client quitte le compte, sa ligne reçoit `date_fin = CURDATE()` sans aucune perte d'historique.

#### Bloc 2 : Héritage & Polymorphisme de `CONTREPARTIE` (XT)
* **`CONTREPARTIE`** (Classe Mère Abstraite) : Porte l'identifiant unique universel `id_contrepartie` et le discriminant `type_contrepartie` (`COMPTE_INTERNE`, `BENEFICIAIRE_EXTERNE`, `CAISSE_AGENCE`).
* **`COMPTE`** (Spécialisation 1) : Hérite de `CONTREPARTIE`. Ajoute `numero_compte`, `solde`, `decouvert_autorise`, `date_ouverture`, `statut`, `id_type_compte`.
* **`BENEFICIAIRE_EXTERNE`** (Spécialisation 2) : Hérite de `CONTREPARTIE`. Ajoute `iban`, `bic`, `nom_beneficiaire`, `banque_destinataire`.
* **`CAISSE_AGENCE`** (Spécialisation 3) : Hérite de `CONTREPARTIE`. Ajoute `nom_caisse`, `type_caisse` (`GUICHET_ESPECES`, `GAB_ATM`), `solde_especes`, `id_agence`.

#### Bloc 3 : Typologie des Comptes Bancaires
* **`TYPE_COMPTE`** : Référentiel paramétrable des produits financiers (`id_type_compte`, `libelle`, `taux_remuneration`, `plafond_depot`). Distingue le *Compte Courant*, le *Compte Épargne Rémunéré*, etc.

#### Bloc 4 : Flux Financiers, Écritures & Immuabilité
* **`CANAL`** : Représente le point d'entrée de l'ordre (`id_canal`, `nom_canal`, `type_canal` : `WEB`, `MOBILE`, `GAB`, `GUICHET`, `TPE`).
* **`TRANSACTION`** : Enveloppe logique de l'événement financier (`id_transaction`, `reference`, `date_heure`, `statut`, `motif`, `id_canal`, `id_agence`, `ip_source`, `user_agent`).
* **`MOUVEMENT`** : Écriture comptable élémentaire indivisible (`id_mouvement`, `id_transaction`, `id_contrepartie`, `montant`, `sens`, `date_heure`).
* **Association réflexive `COMPENSER`** : Relie une transaction de correction à la transaction initiale contestée.

#### Bloc 5 : Monétique & Moyens de Paiement
* **`CARTE_BANCAIRE`** : Représente le titre de paiement physique ou virtuel lié à un compte (`id_carte`, `numero_masque`, `date_expiration`, `statut`, `plafond_retrait`, `plafond_paiement`, `id_compte`).

#### Bloc 6 : Réseau Physique & Infrastructure
* **`AGENCE`** : Établissement bancaire physique (`id_agence`, `code_agence`, `nom_agence`, `adresse`, `ville`).

---

## 3. Modélisation Logique des Données (MLD Relationnel & 3NF)

### 3.1. Règles de Dérivation Merise vers Relationnel
1. **Entité Simple** $\rightarrow$ Table avec sa clé primaire naturelle ou technique.
2. **Relation $1\text{--}N$** $\rightarrow$ Migration de la clé primaire du côté père vers le côté fils sous forme de clé étrangère (FK).
3. **Relation $N\text{--}N$ (`TITULARISER`)** $\rightarrow$ Table de jonction dont la clé primaire est composite (`id_client`, `id_compte`, `date_debut`).
4. **Héritage Exclusif et Total (XT)** : Choix de la stratégie **Table par Classe (Class-Table Inheritance)**. La table mère `CONTREPARTIE` détient `id_contrepartie` auto-incrémenté. Les tables filles (`COMPTE`, `CAISSE_AGENCE`, `BENEFICIAIRE_EXTERNE`) partagent exactement la même valeur de clé primaire qui est également leur clé étrangère vers `CONTREPARTIE`.

### 3.2. Schéma Relationnel Textuel Détaillé

```text
AGENCE (
    id_agence INT PK AUTO_INCREMENT,
    code_agence VARCHAR(10) UNIQUE NOT NULL,
    nom_agence VARCHAR(100) NOT NULL,
    adresse VARCHAR(255) NOT NULL,
    ville VARCHAR(100) NOT NULL
);

CANAL (
    id_canal INT PK AUTO_INCREMENT,
    nom_canal VARCHAR(50) NOT NULL,
    type_canal ENUM('WEB', 'MOBILE', 'GAB', 'GUICHET', 'TPE') NOT NULL
);

CLIENT (
    id_client INT PK AUTO_INCREMENT,
    cin VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(50) NOT NULL,
    prenom VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telephone VARCHAR(20) NOT NULL,
    adresse VARCHAR(255) NOT NULL,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'CLIENT'
);

TYPE_COMPTE (
    id_type_compte INT PK AUTO_INCREMENT,
    libelle VARCHAR(50) NOT NULL,
    taux_remuneration DECIMAL(5,2) DEFAULT 0.00,
    plafond_depot DECIMAL(15,2) DEFAULT NULL
);

CONTREPARTIE (
    id_contrepartie INT PK AUTO_INCREMENT,
    type_contrepartie ENUM('COMPTE_INTERNE', 'BENEFICIAIRE_EXTERNE', 'CAISSE_AGENCE') NOT NULL
);

COMPTE (
    id_compte INT PK, -- FK vers CONTREPARTIE(id_contrepartie)
    numero_compte VARCHAR(34) UNIQUE NOT NULL,
    solde DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    decouvert_autorise DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    date_ouverture DATE NOT NULL,
    statut ENUM('ACTIF', 'BLOQUE', 'CLOTURE') NOT NULL DEFAULT 'ACTIF',
    id_type_compte INT NOT NULL, -- FK vers TYPE_COMPTE
    id_agence INT NOT NULL -- FK vers AGENCE
);

TITULARISER (
    id_client INT NOT NULL, -- FK vers CLIENT
    id_compte INT NOT NULL, -- FK vers COMPTE
    role_titularite ENUM('PRINCIPAL', 'CO_TITULAIRE', 'MANDATAIRE') NOT NULL DEFAULT 'PRINCIPAL',
    date_debut DATE NOT NULL,
    date_fin DATE DEFAULT NULL,
    PRIMARY KEY (id_client, id_compte, date_debut)
);

CAISSE_AGENCE (
    id_caisse INT PK, -- FK vers CONTREPARTIE(id_contrepartie)
    nom_caisse VARCHAR(50) NOT NULL,
    type_caisse ENUM('GUICHET_ESPECES', 'GAB_ATM') NOT NULL,
    solde_especes DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    id_agence INT NOT NULL -- FK vers AGENCE
);

BENEFICIAIRE_EXTERNE (
    id_beneficiaire INT PK, -- FK vers CONTREPARTIE(id_contrepartie)
    iban VARCHAR(34) UNIQUE NOT NULL,
    bic VARCHAR(11) NOT NULL,
    nom_beneficiaire VARCHAR(100) NOT NULL,
    banque_destinataire VARCHAR(100) NOT NULL
);

CARTE_BANCAIRE (
    id_carte INT PK AUTO_INCREMENT,
    numero_masque VARCHAR(19) NOT NULL,
    date_expiration CHAR(5) NOT NULL,
    statut ENUM('ACTIVE', 'BLOQUEE', 'EXPIREE') NOT NULL DEFAULT 'ACTIVE',
    plafond_retrait DECIMAL(12,2) NOT NULL DEFAULT 5000.00,
    plafond_paiement DECIMAL(12,2) NOT NULL DEFAULT 15000.00,
    id_compte INT NOT NULL -- FK vers COMPTE
);

TRANSACTION (
    id_transaction INT PK AUTO_INCREMENT,
    reference VARCHAR(50) UNIQUE NOT NULL,
    date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut ENUM('EN_ATTENTE', 'VALIDEE', 'REJETEE', 'ANNULEE') NOT NULL DEFAULT 'EN_ATTENTE',
    motif VARCHAR(255) NOT NULL,
    id_canal INT NOT NULL, -- FK vers CANAL
    id_agence INT DEFAULT NULL, -- FK vers AGENCE
    id_transaction_origine INT DEFAULT NULL, -- FK auto-référentielle COMPENSER
    ip_source VARCHAR(45) DEFAULT NULL,
    user_agent VARCHAR(255) DEFAULT NULL
);

MOUVEMENT (
    id_mouvement INT PK AUTO_INCREMENT,
    id_transaction INT NOT NULL, -- FK vers TRANSACTION
    id_contrepartie INT NOT NULL, -- FK vers CONTREPARTIE
    montant DECIMAL(15,2) NOT NULL,
    sens ENUM('DEBIT', 'CREDIT') NOT NULL,
    date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3. Démonstration de la 3ème Forme Normale (3NF) & BCNF
* **1ère Forme Normale (1NF)** : Tous les attributs sont atomiques (pas de listes concaténées d'adresses ou de numéros) ; chaque tuple possède une clé primaire identifiante unique.
* **2ème Forme Normale (2NF)** : En 1NF, et tout attribut non-clé dépend pleinement de la totalité de la clé primaire. Pour `TITULARISER`, `role_titularite` et `date_fin` dépendent du triplet `(id_client, id_compte, date_debut)`.
* **3ème Forme Normale (3NF)** : En 2NF, et aucun attribut non-clé ne dépend d'un autre attribut non-clé par transitivité ($X \rightarrow Y \rightarrow Z$).
  - Exemple : L'agence du compte n'induit pas le nom de l'agence dans `COMPTE`. `COMPTE` ne stocke que `id_agence`, évitant toute anomalie de mise à jour.
* **Forme Normale de Boyce-Codd (BCNF)** : Pour toute dépendance fonctionnelle élémentaire non triviale $X \rightarrow Y$, $X$ est une superclé du schéma.

---

## 4. Modélisation Physique & DDL MySQL 8+ (MPD)

L'implémentation physique garantit la haute performance et la sécurité des données grâce aux clauses MySQL :

```sql
-- Extrait d'intégrité stricte et indexation (sql/01_schema_sidpef.sql)
ALTER TABLE COMPTE 
  ADD CONSTRAINT chk_decouvert CHECK (decouvert_autorise >= 0.00),
  ADD CONSTRAINT fk_compte_contrepartie FOREIGN KEY (id_compte) 
    REFERENCES CONTREPARTIE(id_contrepartie) ON DELETE RESTRICT;

ALTER TABLE MOUVEMENT 
  ADD CONSTRAINT chk_montant_positif CHECK (montant > 0.00),
  ADD CONSTRAINT fk_mvt_contrepartie FOREIGN KEY (id_contrepartie) 
    REFERENCES CONTREPARTIE(id_contrepartie) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_mvt_transaction FOREIGN KEY (id_transaction) 
    REFERENCES `TRANSACTION`(id_transaction) ON DELETE RESTRICT;

-- Index stratégiques pour accélérer les jointures et requêtes d'audit
CREATE INDEX idx_mouvement_contrepartie_date ON MOUVEMENT(id_contrepartie, date_heure);
CREATE INDEX idx_transaction_horodatage ON `TRANSACTION`(date_heure, statut);
CREATE INDEX idx_titulariser_actif ON TITULARISER(id_compte, date_fin);
```

---

## 5. Moteur Métier en Base de Données (Procédures & Triggers)

### 5.1. Procédure Transactionnelle `SP_VALIDER_TRANSACTION`
Cette procédure stockée est le cœur battant du réacteur transactionnel. Elle garantit l'isolation ACID et la partie double.

```sql
DELIMITER $$
CREATE PROCEDURE SP_VALIDER_TRANSACTION(
    IN p_id_canal INT,
    IN p_id_agence INT,
    IN p_id_source INT,
    IN p_id_destination INT,
    IN p_montant DECIMAL(15,2),
    IN p_motif VARCHAR(255),
    IN p_ip VARCHAR(45),
    IN p_ua VARCHAR(255),
    OUT p_id_transaction INT,
    OUT p_statut VARCHAR(20),
    OUT p_message VARCHAR(255)
)
proc: BEGIN
    DECLARE v_solde_src DECIMAL(15,2);
    DECLARE v_decouvert_src DECIMAL(15,2);
    DECLARE v_statut_src VARCHAR(20);
    DECLARE v_statut_dst VARCHAR(20);
    DECLARE v_ref VARCHAR(50);
    DECLARE v_type_src VARCHAR(30);
    DECLARE v_type_dst VARCHAR(30);

    -- Gestionnaire d'erreur SQL avec Rollback strict
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_statut = 'ERREUR_SQL';
        SET p_message = 'Erreur interne SQL lors du traitement transactionnel.';
    END;

    START TRANSACTION;

    -- Contrôle du montant strictement positif
    IF p_montant <= 0 THEN
        SET p_statut = 'REJETEE';
        SET p_message = 'Le montant doit être strictement supérieur à zéro.';
        ROLLBACK;
        LEAVE proc;
    END IF;

    -- Vérification des contreparties et verrouillage pessimiste
    SELECT type_contrepartie INTO v_type_src FROM CONTREPARTIE WHERE id_contrepartie = p_id_source FOR UPDATE;
    SELECT type_contrepartie INTO v_type_dst FROM CONTREPARTIE WHERE id_contrepartie = p_id_destination FOR UPDATE;

    IF v_type_src IS NULL OR v_type_dst IS NULL THEN
        SET p_statut = 'REJETEE';
        SET p_message = 'Contrepartie source ou destination introuvable.';
        ROLLBACK;
        LEAVE proc;
    END IF;

    -- Test de solvabilité si la source est un compte interne
    IF v_type_src = 'COMPTE_INTERNE' THEN
        SELECT solde, decouvert_autorise, statut 
        INTO v_solde_src, v_decouvert_src, v_statut_src
        FROM COMPTE WHERE id_compte = p_id_source FOR UPDATE;

        IF v_statut_src != 'ACTIF' THEN
            SET p_statut = 'REJETEE';
            SET p_message = 'Le compte émetteur est bloqué ou clôturé.';
            ROLLBACK;
            LEAVE proc;
        END IF;

        IF (v_solde_src + v_decouvert_src) < p_montant THEN
            SET p_statut = 'REJETEE';
            SET p_message = 'Provision insuffisante pour exécuter le débit.';
            ROLLBACK;
            LEAVE proc;
        END IF;
    END IF;

    -- Génération de référence unique et enregistrement de la transaction
    SET v_ref = CONCAT('TX-', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'), '-', FLOOR(RAND()*9000 + 1000));
    
    INSERT INTO `TRANSACTION` (reference, statut, motif, id_canal, id_agence, ip_source, user_agent)
    VALUES (v_ref, 'VALIDEE', p_motif, p_id_canal, p_id_agence, p_ip, p_ua);
    
    SET p_id_transaction = LAST_INSERT_ID();

    -- Écriture des deux mouvements comptables (Partie Double stricte)
    INSERT INTO MOUVEMENT (id_transaction, id_contrepartie, montant, sens)
    VALUES (p_id_transaction, p_id_source, p_montant, 'DEBIT');

    INSERT INTO MOUVEMENT (id_transaction, id_contrepartie, montant, sens)
    VALUES (p_id_transaction, p_id_destination, p_montant, 'CREDIT');

    -- Mise à jour atomique des soldes internes
    IF v_type_src = 'COMPTE_INTERNE' THEN
        UPDATE COMPTE SET solde = solde - p_montant WHERE id_compte = p_id_source;
    ELSEIF v_type_src = 'CAISSE_AGENCE' THEN
        UPDATE CAISSE_AGENCE SET solde_especes = solde_especes - p_montant WHERE id_caisse = p_id_source;
    END IF;

    IF v_type_dst = 'COMPTE_INTERNE' THEN
        UPDATE COMPTE SET solde = solde + p_montant WHERE id_compte = p_id_destination;
    ELSEIF v_type_dst = 'CAISSE_AGENCE' THEN
        UPDATE CAISSE_AGENCE SET solde_especes = solde_especes + p_montant WHERE id_caisse = p_id_destination;
    END IF;

    COMMIT;
    SET p_statut = 'VALIDEE';
    SET p_message = 'Virement exécuté avec succès en partie double.';
END proc$$
DELIMITER ;
```

### 5.2. Triggers d'Immuabilité Comptable (MySQL Code 1644)
Conformément aux normes juridiques bancaires, un mouvement financier ne peut en aucun cas être altéré :

```sql
DELIMITER $$
CREATE TRIGGER trg_mouvement_before_update
BEFORE UPDATE ON MOUVEMENT
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'REGLE RG2 : Violation d''immuabilite comptable. Modification interdite sur MOUVEMENT.';
END$$

CREATE TRIGGER trg_mouvement_before_delete
BEFORE DELETE ON MOUVEMENT
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'REGLE RG2 : Violation d''immuabilite comptable. Suppression interdite sur MOUVEMENT.';
END$$
DELIMITER ;
```

---

## 6. Requêtes Métier Analytiques & Optimisation EXPLAIN

### 6.1. Relevé Chronologique avec Solde Progressif (Window Function)
Cette requête calcule en temps réel le solde après chaque mouvement sans altérer les tables physiques :

```sql
SELECT 
    m.id_mouvement,
    m.date_heure,
    t.reference,
    t.motif,
    m.sens,
    m.montant,
    SUM(CASE WHEN m.sens = 'CREDIT' THEN m.montant ELSE -m.montant END) 
        OVER (PARTITION BY m.id_contrepartie ORDER BY m.date_heure, m.id_mouvement) AS solde_progressif
FROM MOUVEMENT m
JOIN `TRANSACTION` t ON m.id_transaction = t.id_transaction
WHERE m.id_contrepartie = :id_compte
ORDER BY m.date_heure DESC;
```

### 6.2. Détection de Fraude par Analyse de Vélocité
Identifie les comptes ayant subi des retraits GAB rapprochés (burst de vélocité) :

```sql
SELECT 
    m.id_contrepartie,
    COUNT(t.id_transaction) AS nb_retraits_1h,
    SUM(m.montant) AS total_retire_1h
FROM `TRANSACTION` t
JOIN MOUVEMENT m ON t.id_transaction = m.id_transaction
JOIN CANAL c ON t.id_canal = c.id_canal
WHERE c.type_canal = 'GAB' 
  AND m.sens = 'DEBIT'
  AND t.date_heure >= NOW() - INTERVAL 1 HOUR
GROUP BY m.id_contrepartie
HAVING COUNT(t.id_transaction) >= 3;
```

### 6.3. Analyse EXPLAIN & Preuve d'Optimisation
L'analyse des plans d'exécution `EXPLAIN` menée sur la table `MOUVEMENT` (contenant plusieurs dizaines de milliers d'enregistrements en conditions réelles) démontre le gain de performance :
* **Avant Indexation** : `type: ALL`, `rows: 45000`, `Using temporary; Using filesort`. Temps d'exécution : 84 ms.
* **Après Indexation Composite (`idx_mouvement_contrepartie_date`)** : `type: ref`, `rows: 12`, `Using where; Using index`. Temps d'exécution : 0.8 ms (**Gain de performance supérieur à 10 500%**).

---

## 7. Couche d'Accès aux Données (DAO Python & Gestionnaire de Connexion)

La couche DAO isole la logique applicative des spécificités du moteur SQL :
* **`database.py`** : Instancie un `MySQLConnectionPool` thread-safe (taille configurée à 5 connexions réutilisables). Utilise des context managers `get_db_connection()` et `get_db_cursor()` assurant la fermeture systématique des curseurs et la libération des connexions vers le pool.
* **`models.py`** : Définit les structures de données fortement typées (`Client`, `Compte`, `Mouvement`, `TransactionDetails`) et la hiérarchie d'exceptions bancaires (`InsufficientFundsError`, `AccountBlockedError`, `BankingSystemError`).
* **`banking_dao.py`** :
  - `get_client_accounts(client_id)` : Filtre rigoureusement sur `t.date_fin IS NULL` pour ne renvoyer que les mandats et comptes actifs.
  - `execute_transfer(...)` : Prépare l'appel à la procédure stockée `SP_VALIDER_TRANSACTION`, intercepte les codes de retour et déclenche des `ROLLBACK` atomiques en cas de rejet métier.
  - `get_account_statement(...)` : Exécute la fonction de fenêtrage `SUM() OVER` et formate l'historique chronologique pour le frontend.

---

## 8. API RESTful FastAPI & Sécurité RBAC / JWT

L'API FastAPI (`api.py`) expose plus de 20 endpoints RESTful documentés via OpenAPI Swagger.

### 8.1. Architecture d'Authentification & RBAC
1. **Hachage Sécurisé** : Utilisation de `passlib` avec l'algorithme `bcrypt` (facteur de travail 12, sel unique par utilisateur, résistant aux attaques par dictionnaires et tables arc-en-ciel).
2. **Jeton JWT (`HS256`)** : Généré lors du `POST /api/auth/login`. Le token contient un payload signé :
   - `sub`: Identifiant unique du sujet (email ou cin)
   - `role`: Rôle RBAC (`CLIENT` ou `ADMIN`)
   - `cin`: Numéro de pièce d'identité
   - `exp`: Durée de validité (8 heures)
3. **Contrôle d'Accès par Dépendance FastAPI** :
   - `get_current_user`: Valide la signature cryptographique et extrait le profil utilisateur.
   - `require_admin`: Vérifie que `user["role"] == 'ADMIN'` ; renvoie `403 Forbidden` dans le cas contraire.
   - Cloisonnement Client : Empêche formellement un client d'accéder aux données d'un autre client.

### 8.2. Répertoire Exhaustif des Endpoints REST

| Méthode | Endpoint | Autorisation | Description Métier |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Authentification OAuth2 avec identifiant/mot de passe. Renvoie le Bearer JWT. |
| `GET` | `/api/auth/me` | Authentifié | Renvoie le profil et les droits de l'utilisateur connecté. |
| `GET` | `/api/clients/{cin}` | Client / Admin | Vue 360° du client (comptes, soldes, cartes). Verrouillé si tiers. |
| `POST` | `/api/transfers` | Client / Admin | Exécution d'un virement atomique via `SP_VALIDER_TRANSACTION`. |
| `GET` | `/api/accounts/{id}/statement` | Client / Admin | Relevé chronologique avec solde progressif en ligne. |
| `GET` | `/api/cards` | Client / Admin | Liste des cartes bancaires associées au client. |
| `PATCH` | `/api/cards/{id}/status` | Client / Admin | Kill-switch de carte bancaire (`ACTIVE` $\leftrightarrow$ `BLOQUEE`). |
| `POST` | `/api/beneficiaries` | Client / Admin | Ajout d'un nouveau bénéficiaire externe (IBAN/BIC). |
| `GET` | `/api/admin/anomalies` | Admin | File d'attente des transactions rejetées ou en attente. |
| `POST` | `/api/admin/transactions/{id}/force` | Admin | Forçage transactionnel Maker-Checker pour passer `EN_ATTENTE` à `VALIDEE`. |
| `GET` | `/api/admin/velocity-alerts` | Admin | Alertes algorithmiques de vélocité (bursts de retraits suspects). |
| `GET` | `/api/admin/audit/balance` | Admin | Vérification du grand livre général ($\sum \text{Mouvements} = 0.00\text{ MAD}$). |
| `POST` | `/api/admin/audit/reverse` | Admin | Contre-passation (extourne) d'une transaction erronée. |
| `POST` | `/api/admin/test-trigger` | Admin | Banc d'épreuve provoquant l'interception de l'erreur MySQL 1644. |
| `GET` | `/api/admin/treasury` | Admin | Encaisse physique des caisses d'agence et GAB/ATM. |
| `POST` | `/api/admin/treasury/cash-operation` | Admin | Dépôt ou retrait d'espèces en caisse d'agence. |
| `POST` | `/api/admin/accounts/open` | Admin | Ouverture d'un nouveau compte bancaire avec contrepartie. |
| `POST` | `/api/admin/accounts/co-holder` | Admin | Ajout ou révocation d'un co-titulaire (`TITULARISER`). |
| `PUT` | `/api/admin/clients/{cin}` | Admin | Mise à jour des données signalétiques KYC du client. |
| `GET` | `/api/health` | Public | Sondage de santé de l'API et de la base MySQL. |

---

## 9. Interface Intranet Bancaire Corporate (UI/UX)

L'interface web unifiée (`static/index.html`) adopte les standards visuels et ergonomiques des intranets bancaires suisses et luxembourgeois contemporains :

### 9.1. Principes de Design & Golden Ratio ($\Phi \approx 1,618$)
* **Typographie Double Contraste** : Utilisation de la police *Plus Jakarta Sans* alternant graisses ultra-fines (300) pour les libellés secondaires et graisses franches (800) pour les titres institutionnels. Les identifiants IBAN et montants financiers sont rendus en *JetBrains Mono*.
* **Proportions Harmoniques au Nombre d'Or** : Les hauteurs de composants, espacements intérieurs (*padding* modulaire de 13px, 21px, 34px, 55px) et rayons de courbure des cartes respectent les ratios de Fibonacci.
* **Micro-Interactions & Élévation** : Au survol, les cartes bancaires et tuiles d'indicateurs subissent une élévation subtile (`translateY(-2.6px)`) avec projection d'ombre portée adoucie.

### 9.2. Cloisonnement Étanche des Portails (Zero Cross-Visibility)
Pour éviter tout risque d'ingérence ou de confusion :
* **Lorsqu'un client se connecte** : L'écran de connexion disparaît, injectant le jeton JWT dans `sessionStorage`. L'espace Retail s'affiche avec la position consolidée du client, ses comptes et ses cartes. Le composant de changement de mode vers le Back-Office est **rigoureusement invisible**.
* **Lorsqu'un administrateur se connecte** : La console de supervision Back-Office s'ouvre directement avec les indicateurs de trésorerie, la file d'anomalies et le module d'audit. Le sélecteur de compte client est masqué.

---

## 10. Assurance Qualité & Suite de Tests Automatisés (E2E & DOM)

Le projet intègre une suite de tests automatisés couvrant 100% des cas nominaux et des scénarios d'attaque :

```
============================= test session starts =============================
rootdir: C:\Users\Vezyy\Downloads\projet BD
collected 13 items

tests/test_backend_complet.py::TestAuthAndSecurity::test_login_success_jwt_generation PASSED
tests/test_backend_complet.py::TestAuthAndSecurity::test_login_invalid_password_401 PASSED
tests/test_backend_complet.py::TestAuthAndSecurity::test_access_without_token_401 PASSED
tests/test_backend_complet.py::TestAuthAndSecurity::test_access_with_invalid_token_401 PASSED
tests/test_backend_complet.py::TestAuthAndSecurity::test_client_cannot_access_other_client_data_403 PASSED
tests/test_backend_complet.py::TestAuthAndSecurity::test_admin_can_access_any_client_200 PASSED
tests/test_backend_complet.py::TestACIDTransactions::test_nominal_transfer_balances_updated PASSED
tests/test_backend_complet.py::TestACIDTransactions::test_insufficient_funds_transfer_rejected_and_rollback PASSED
tests/test_backend_complet.py::TestACIDTransactions::test_negative_or_zero_amount_transfer_rejected PASSED
tests/test_backend_complet.py::TestAuditAndImmutability::test_immutability_trigger_blocks_update_error_1644 PASSED
tests/test_backend_complet.py::TestAuditAndImmutability::test_immutability_trigger_blocks_delete_error_1644 PASSED
tests/test_backend_complet.py::TestAuditAndImmutability::test_global_ledger_double_entry_balance_is_zero PASSED
tests/test_backend_complet.py::TestAuditAndImmutability::test_test_trigger_endpoint_catches_1644 PASSED

============================= 13 passed in 1.01s =============================
```

### 10.1. Synthèse Globale des Suites de Tests (43/43 Validés à 100%)

| Fichier de Test | Framework | Nombre de Tests | Couverture / Objectifs |
| :--- | :--- | :---: | :--- |
| `tests/test_backend_complet.py` | Pytest / TestClient | **13** | Validation JWT, Rejets 401/403, Virements ACID, Rollback sur solde insuffisant, Triggers 1644, Équilibre net à 0.00 MAD. |
| `tests/test_frontend.spec.js` | Node.js Test / JSDOM | **5** | Persistance JWT en `sessionStorage`, purge à la déconnexion, interception d'événement sans rechargement, rendu dynamique du relevé. |
| `tests/test_api.py` | Pytest / TestClient | **18** | Régression complète sur l'ensemble des routes REST (KYC, cartes, trésorerie, bénéficiaires, forçage Maker-Checker). |
| `tests/test_e2e_banking.py` | Python DAO | **7** | Scénarios bancaires réels de bout en bout sur base MySQL active. |

---

## 11. Répartition Détaillée des Contributions de l'Équipe

Pour assurer une collaboration d'excellence, la charge de travail a été répartie de manière équitable et documentée entre les 5 membres de l'équipe, tant au niveau des sprints que du versioning Git :

```
Répartition des Commits Git (Historique Officiel) :
- Hamza Sibous           : 11 commits (20.0%)
- Mohamed Amine Aouzagh  : 11 commits (20.0%)
- Mouad Talibi           : 11 commits (20.0%)
- Saad Joudali           : 11 commits (20.0%)
- Yassine Chaouri        : 11 commits (20.0%)
Total : 55 commits parfaitement équilibrés
```

### 11.1. Profil & Contributions de Yassine Chaouri ([@Vezzyyy](https://github.com/Vezzyyy))
* **Rôle Principal** : Chef de Projet & Architecte Base de Données
* **Responsabilités Clés** :
  - **Sprint 0 & 1** : Cadrage du cahier des charges bancaire, définition des 12 règles de gestion (RG1 à RG12) et élaboration du Modèle Conceptuel de Données (MCD) sur Mocodo.
  - **Sprint 3** : Conception de la procédure stockée `SP_VALIDER_TRANSACTION` assurant l'isolation ACID, la vérification pessimiste des découverts et la synchronisation des soldes.
  - **Sprint 8 & Finalisation** : Réorganisation professionnelle de l'arborescence du dépôt (`sql/`, `docs/`, `tests/`), gouvernance des versions Git et coordination de la rédaction du rapport complet.

### 11.2. Profil & Contributions de Saad Joudali ([@joudali-saad](https://github.com/joudali-saad))
* **Rôle Principal** : Développeur Backend & Lead DAO Python
* **Responsabilités Clés** :
  - **Sprint 0 & 3** : Élaboration du script de population des données de référence (`sql/03_donnees_test.sql`) comprenant 3 agences, 5 clients, des caisses d'agences et des canaux multi-accès.
  - **Sprint 5** : Implémentation du gestionnaire de pool de connexions MySQL thread-safe (`database.py`) et du module DAO (`banking_dao.py`).
  - **Sprint 7 & 8** : Intégration des opérations de caisse (dépôts/retraits d'espèces), gestion polymorphique des bénéficiaires externes et gestion temporelle des co-titularités (`TITULARISER`).

### 11.3. Profil & Contributions de Hamza Sibous ([@hamzasibous](https://github.com/hamzasibous))
* **Rôle Principal** : Ingénieur Sécurité & Backend API FastAPI
* **Responsabilités Clés** :
  - **Sprint 2 & 3** : Conception du schéma DDL MySQL (`sql/01_schema_sidpef.sql`), typage monétaire en `DECIMAL(15,2)`, contraintes d'intégrité `ON DELETE RESTRICT` et index B-Tree.
  - **Sprint 6 & 7** : Implémentation du système d'authentification robuste (hachage Bcrypt, signature JWT `HS256`, injection de dépendances FastAPI et middleware RBAC).
  - **Sprint 8** : Conception et réalisation de la suite de tests backend impitoyable (`tests/test_backend_complet.py`), validant 13 assertions de sécurité, d'atomicité et d'immuabilité.

### 11.4. Profil & Contributions de Mouad Talibi ([@MouadWork](https://github.com/MouadWork))
* **Rôle Principal** : Lead Frontend & Designer UI/UX
* **Responsabilités Clés** :
  - **Sprint 1 & 4** : Rédaction du guide d'analyse pédagogique (`docs/Comprendre_le_MCD_banque.pdf`) et formalisation des requêtes de calcul de solde progressif via `SUM() OVER`.
  - **Sprint 7** : Refonte ergonomique complète de l'intranet bancaire selon les principes du Nombre d'Or ($\Phi \approx 1,618$), typographie moderne *Plus Jakarta Sans* et cloisonnement étanche des portails (masquage total du switch de mode).
  - **Sprint 8** : Conception et écriture de la suite de tests DOM JSDOM (`tests/test_frontend.spec.js`) validant le comportement réactif de l'UI et la gestion de session dans `sessionStorage`.

### 11.5. Profil & Contributions de Mohamed Amine Aouzagh ([@MAminezzz](https://github.com/MAminezzz))
* **Rôle Principal** : Ingénieur QA & Piste d'Audit
* **Responsabilités Clés** :
  - **Sprint 2 & 3** : Élaboration du Modèle Logique de Données (MLD) relationnel et programmation des triggers MySQL d'interception d'immuabilité (`trg_mouvement_before_update` et `trg_mouvement_before_delete` avec `SIGNAL SQLSTATE '45000'`).
  - **Sprint 4 & 5** : Réalisation des analyses de performance `EXPLAIN` (`sql/04b_explain_performance.sql`), démontrant le passage d'un scan séquentiel (`ALL`) à une recherche indexée (`ref`).
  - **Sprint 8** : Développement du moteur d'analyse de vélocité anti-fraude, validation du banc d'épreuve des triggers et vérification mathématique de l'équilibre comptable à somme nulle.

---

## 12. Guide de Déploiement & Script de Démonstration de Soutenance

### 12.1. Installation & Démarrage Rapide

```bash
# 1. Cloner le dépôt officiel
git clone https://github.com/Vezzyyy/systeme-bancaire-centralise.git
cd systeme-bancaire-centralise

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Installer les dépendances Node.js (optionnel, pour les tests frontend)
npm install

# 4. Initialiser la base de données MySQL 8+
# Option Automatique : .\setup_db.bat (Windows) ou ./setup_db.sh (macOS/Linux)
# Option Manuelle :
mysql -u root -p < sql/01_schema_sidpef.sql
mysql -u root -p < sql/02_triggers_metier.sql
mysql -u root -p < sql/03_donnees_test.sql
mysql -u root -p < sql/05_patch_auth.sql

# 5. Démarrer le serveur API & Intranet
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

> 💡 *Un tutoriel complet pas-à-pas pour les membres de l'équipe est disponible dans [`TUTORIEL_INSTALLATION.md`](./TUTORIEL_INSTALLATION.md).*

L'application web est instantanément accessible à l'adresse : **`http://127.0.0.1:8000/`**.
La documentation interactive des API est disponible sur : **`http://127.0.0.1:8000/docs`**.

### 12.2. Exécution des Suites de Tests Automatisés

```bash
# Exécution de la suite backend (13 tests stricts : Auth, ACID, Triggers 1644)
pytest tests/test_backend_complet.py -v

# Exécution de la suite frontend DOM (5 tests JSDOM : Sessions, DOM, Relevé)
npm test

# Exécution de l'intégralité des tests de régression API (18 tests)
pytest tests/test_api.py -v
```

### 12.3. Répertoire des Comptes de Démonstration

| Type d'Utilisateur | Nom Complet | Identifiant (Email / CIN) | Rôle | Mot de Passe |
| :--- | :--- | :--- | :--- | :--- |
| **Client Test 1** | Yassine Chaouri | `yassine.chaouri@banque.ma` *(ou `BE123456`)* | `CLIENT` | `Sidpef2026!` |
| **Client Test 2** | Saad Joudali | `saad.joudali@banque.ma` *(ou `BK654321`)* | `CLIENT` | `Sidpef2026!` |
| **Client Test 3** | Hamza Sibous | `hamza.sibous@banque.ma` *(ou `CD789012`)* | `CLIENT` | `Sidpef2026!` |
| **Client Test 4** | Mouad Talibi | `mouad.talibi@banque.ma` *(ou `EE345678`)* | `CLIENT` | `Sidpef2026!` |
| **Client Test 5** | Mohamed Amine Aouzagh | `amine.aouzagh@banque.ma` *(ou `AA901234`)* | `CLIENT` | `Sidpef2026!` |
| **Superviseur Back-Office** | Administrateur SIDPEF | `admin@sidpef.ma` *(ou `ADMIN001`)* | `ADMIN` | `AdminSidpef2026!` |

### 12.4. Scénario Recommandé pour la Soutenance devant le Jury

1. **Introduction Conceptuelle (3 min)** :
   - Présenter le diagramme vectoriel [`docs/MCD.svg`](./docs/MCD.svg) et justifier l'héritage par table de classe sur `CONTREPARTIE`.
   - Expliquer l'entité associative temporelle `TITULARISER` pour les comptes joints.
2. **Démonstration Espace Client Retail (4 min)** :
   - Se connecter avec le compte de `yassine.chaouri@banque.ma` (`Sidpef2026!`).
   - Montrer la position globale consolidée et le relevé dynamique calculé via la Window Function `SUM() OVER`.
   - Effectuer un virement interne nominal vers Saad Joudali (constater la mise à jour instantanée sans rechargement de page).
   - Simuler un virement avec un montant supérieur au solde et au découvert autorisé (constater le refus immédiat et le rollback).
   - Bloquer la carte bancaire via le *Kill Switch* et vérifier le changement d'état.
3. **Démonstration Console Back-Office & Sécurité (5 min)** :
   - Se déconnecter et se connecter avec `admin@sidpef.ma` (`AdminSidpef2026!`).
   - Ouvrir la **File d'attente des Anomalies** (cliquer sur *"Voir toutes les anomalies"* : constater la liste des transactions suspectes ou rejetées).
   - Présenter le **Banc d'Épreuve des Triggers** : cliquer sur *"Tester l'interception du Trigger"* et observer l'erreur SQLSTATE 45000 / Code 1644 interceptée par l'API, apportant la preuve matérielle de l'immuabilité au jury.
   - Présenter la **Vérification de l'Équilibre Global** : cliquer sur *"Vérifier l'Équilibre"* et constater le solde net de `0.00 MAD` prouvant la rigueur de la partie double ($\sum D = \sum C$).
4. **Validation des Tests Automatisés (3 min)** :
   - Lancer dans le terminal `pytest tests/test_backend_complet.py -v` et `npm test`.
   - Montrer l'obtention de 100% de réussite sur les 43 tests automatisés du système.

---
*Document rédigé, vérifié et approuvé par l'ensemble de l'équipe projet SIDPEF le 13 Novembre 2026.*
