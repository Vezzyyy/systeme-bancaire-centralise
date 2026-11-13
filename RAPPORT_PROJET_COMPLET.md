# RAPPORT DE PROJET COMPLET â€” SYSTÃˆME BANCAIRE CENTRALISÃ‰ (SIDPEF)
## *Core Banking Information System, ModÃ©lisation Merise 3NF, Moteur Transactionnel MySQL 8+, API FastAPI & Intranet Bancaire SÃ©curisÃ©*

---

### ðŸ“‹ Fiche SignalÃ©tique du Projet

* **IntitulÃ© Officiel** : Conception, ModÃ©lisation, ImplÃ©mentation et SÃ©curisation d'un SystÃ¨me Bancaire CentralisÃ© (*SIDPEF - SystÃ¨me d'Information et de DonnÃ©es des Paiements et Ã‰critures FinanciÃ¨res*)
* **MÃ©thodologie de Conception** : Merise (ModÃ¨le Conceptuel, Logique et Physique de DonnÃ©es)
* **SGBD Transactionnel** : MySQL 8.0+ (Moteur InnoDB, ACID strict, Triggers d'ImmuabilitÃ©, ProcÃ©dures StockÃ©es)
* **Couche Applicative Backend** : Python 3.12+ / FastAPI / Pydantic V2 / Uvicorn / MySQL Connector Pooling
* **SÃ©curitÃ© & Authentification** : JWT (JSON Web Tokens `HS256`), Hachage Cryptographique Bcrypt, ContrÃ´le d'AccÃ¨s BasÃ© sur les RÃ´les (RBAC)
* **Interface Utilisateur** : Intranet Bancaire SPA Haute FidÃ©litÃ© (HTML5, CSS3 Moderne, Vanilla JS ES2024, Typographie *Plus Jakarta Sans* & *JetBrains Mono*, HiÃ©rarchie visuelle au Nombre d'Or $\Phi \approx 1,618$)
* **Assurance QualitÃ© & Tests** : 43 tests automatisÃ©s (Pytest, JSDOM, FastAPI TestClient, E2E DAO) avec 100% de taux de rÃ©ussite
* **DÃ©pÃ´t GitHub** : [github.com/Vezzyyy/systeme-bancaire-centralise](https://github.com/Vezzyyy/systeme-bancaire-centralise)
* **Membres du Projet** :
  1. **Yassine Chaouri** ([@Vezzyyy](https://github.com/Vezzyyy)) â€” Chef de Projet & Architecte Base de DonnÃ©es
  2. **Saad Joudali** ([@joudali-saad](https://github.com/joudali-saad)) â€” DÃ©veloppeur Backend & Lead DAO Python
  3. **Hamza Sibous** ([@hamzasibous](https://github.com/hamzasibous)) â€” IngÃ©nieur SÃ©curitÃ© & Backend API FastAPI
  4. **Mouad Talibi** ([@MouadWork](https://github.com/MouadWork)) â€” Lead Frontend & Designer UI/UX
  5. **Mohamed Amine Aouzagh** ([@MAminezzz](https://github.com/MAminezzz)) â€” IngÃ©nieur QA & Automatisation des Tests

---

## ðŸ“‘ TABLE DES MATIÃˆRES

1. [Introduction, Contexte & Exigences MÃ©tier](#1-introduction-contexte--exigences-mÃ©tier)
2. [ModÃ©lisation Conceptuelle des DonnÃ©es (MCD Merise)](#2-modÃ©lisation-conceptuelle-des-donnÃ©es-mcd-merise)
3. [ModÃ©lisation Logique des DonnÃ©es (MLD Relationnel & 3NF)](#3-modÃ©lisation-logique-des-donnÃ©es-mld-relationnel--3nf)
4. [ModÃ©lisation Physique & DDL MySQL 8+ (MPD)](#4-modÃ©lisation-physique--ddl-mysql-8-mpd)
5. [Moteur MÃ©tier en Base de DonnÃ©es (ProcÃ©dures & Triggers)](#5-moteur-mÃ©tier-en-base-de-donnÃ©es-procÃ©dures--triggers)
6. [RequÃªtes MÃ©tier Analytiques & Optimisation EXPLAIN](#6-requÃªtes-mÃ©tier-analytiques--optimisation-explain)
7. [Couche d'AccÃ¨s aux DonnÃ©es (DAO Python & Gestionnaire de Connexion)](#7-couche-daccÃ¨s-aux-donnÃ©es-dao-python--gestionnaire-de-connexion)
8. [API RESTful FastAPI & SÃ©curitÃ© RBAC / JWT](#8-api-restful-fastapi--sÃ©curitÃ©-rbac--jwt)
9. [Interface Intranet Bancaire Corporate (UI/UX)](#9-interface-intranet-bancaire-corporate-uiux)
10. [Assurance QualitÃ© & Suite de Tests AutomatisÃ©s (E2E & DOM)](#10-assurance-qualitÃ©--suite-de-tests-automatisÃ©s-e2e--dom)
11. [RÃ©partition DÃ©taillÃ©e des Contributions de l'Ã‰quipe](#11-rÃ©partition-dÃ©taillÃ©e-des-contributions-de-lÃ©quipe)
12. [Guide de DÃ©ploiement & Script de DÃ©monstration de Soutenance](#12-guide-de-dÃ©ploiement--script-de-dÃ©monstration-de-soutenance)

---

## 1. Introduction, Contexte & Exigences MÃ©tier

### 1.1. Contexte du Core Banking
Le secteur bancaire repose sur un impÃ©ratif fondamental : la **confiance absolue** dans l'intÃ©gritÃ©, la traÃ§abilitÃ© et l'exactitude des Ã©critures financiÃ¨res. Tout systÃ¨me d'information bancaire centralisÃ© (*Core Banking System*) doit rÃ©pondre aux standards rÃ©glementaires internationaux les plus stricts (Accords de BÃ¢le III, normes PCI-DSS pour la monÃ©tique, rÃ©glementations anti-blanchiment AML/KYC et normes comptables de double saisie).

Le systÃ¨me **SIDPEF** a Ã©tÃ© conÃ§u pour concilier deux exigences majeures :
1. **L'InviolabilitÃ© Comptable & Transactionnelle** : Aucune somme d'argent ne peut Ãªtre crÃ©Ã©e ou dÃ©truite unilatÃ©ralement. Chaque opÃ©ration doit respecter le principe de la comptabilitÃ© en partie double ($\sum \text{DÃ©bits} = \sum \text{CrÃ©dits}$).
2. **L'ImmuabilitÃ© de la Piste d'Audit** : Il est juridiquement et techniquement interdit de modifier ou de supprimer une Ã©criture financiÃ¨re validÃ©e. Toute correction d'erreur doit s'opÃ©rer par *contre-passation* (extourne).

### 1.2. Principes Directeurs de Conception (RÃ¨gles de Gestion RG1 Ã  RG12)
- **RG1 (Partie Double)** : Tout mouvement dÃ©biteur sur une contrepartie doit Ãªtre rigoureusement Ã©quilibrÃ© par un mouvement crÃ©diteur d'Ã©gal montant sur une autre contrepartie au sein de la mÃªme transaction.
- **RG2 (ImmuabilitÃ© Stricte)** : Les tables de journalisation comptable (`MOUVEMENT`) sont interdites de `UPDATE` et de `DELETE` via des triggers bloquants (`SIGNAL SQLSTATE '45000'`).
- **RG3 (Extourne / Contre-passation)** : L'annulation d'une transaction erronÃ©e gÃ©nÃ¨re une nouvelle transaction opposÃ©e liÃ©e Ã  la premiÃ¨re par l'association rÃ©flexive `COMPENSER`.
- **RG4 (DÃ©couplage Titulaire-Compte)** : Un client n'est pas liÃ© directement Ã  un compte par une clÃ© Ã©trangÃ¨re fixe, mais par l'entitÃ© associative `TITULARISER` permettant la co-titularitÃ©, les procurations et l'historisation temporelle (`date_debut`, `date_fin`).
- **RG5 (Polymorphisme des Flux)** : Tous les flux financiers ciblent une `CONTREPARTIE` abstraite, spÃ©cialisÃ©e en compte interne (`COMPTE`), bÃ©nÃ©ficiaire externe (`BENEFICIAIRE_EXTERNE`) ou encaisse physique d'agence (`CAISSE_AGENCE`).
- **RG6 (SolvabilitÃ© & DÃ©couvert AutorisÃ©)** : Un compte bancaire ne peut Ãªtre dÃ©bitÃ© que si le montant ne dÃ©passe pas son solde courant majorÃ© de son dÃ©couvert contractuel autorisÃ© ($Solde + DecouvertAutorise \ge Montant$).
- **RG7 (Multi-Canal & TraÃ§abilitÃ© Technique)** : Toute transaction enregistre son canal d'initiation (GAB, Guichet, Web, Mobile) ainsi que l'adresse IP et le User-Agent de la session.
- **RG8 (MonÃ©tique & Plafonds)** : Chaque carte bancaire est attachÃ©e Ã  un compte actif et dispose de plafonds distincts de retrait et de paiement, ainsi que d'un commutateur d'Ã©tat d'urgence (*Kill Switch*).
- **RG9 (SÃ©paration des Pouvoirs Maker-Checker)** : Un utilisateur simple ne peut valider une transaction suspecte ou Ã  haut risque ; celle-ci est placÃ©e en anomalie (`EN_ATTENTE` ou `REJETEE`) et requiert l'intervention d'un superviseur Back-Office.
- **RG10 (Cloisonnement des DonnÃ©es Client)** : Un client ne peut en aucun cas consulter les comptes, cartes ou mouvements d'un tiers (`403 Forbidden`).
- **RG11 (IntÃ©gritÃ© RÃ©fÃ©rentielle Restrictive)** : Toutes les clÃ©s Ã©trangÃ¨res financiÃ¨res sont configurÃ©es en `ON DELETE RESTRICT` afin de bannir les suppressions en cascade accidentelles.
- **RG12 (ZÃ©ro Net Global)** : Ã€ tout instant, la somme algÃ©brique globale de tous les mouvements enregistrÃ©s dans le systÃ¨me bancaire doit Ãªtre exactement Ã©gale Ã  `0.00 MAD`.

---

## 2. ModÃ©lisation Conceptuelle des DonnÃ©es (MCD Merise)

Le ModÃ¨le Conceptuel de DonnÃ©es (MCD) a Ã©tÃ© modÃ©lisÃ© selon la mÃ©thode Merise pour formaliser la sÃ©mantique mÃ©tier indÃ©pendamment de tout choix technique d'implÃ©mentation.

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

#### Bloc 1 : ClientÃ¨le, KYC & TitularitÃ©s Temporelles
* **`CLIENT`** : Identifie la personne physique ou morale (`id_client`, `cin`, `nom`, `prenom`, `email`, `telephone`, `adresse`, `mot_de_passe_hash`, `role`).
* **`TITULARISER`** : Relation porteuse de donnÃ©es temporelles (`id_client`, `id_compte`, `role_titularite`, `date_debut`, `date_fin`).
  - *RÃ¨gle d'or* : Un compte joint associe plusieurs clients avec `date_fin IS NULL`. Si un client quitte le compte, sa ligne reÃ§oit `date_fin = CURDATE()` sans aucune perte d'historique.

#### Bloc 2 : HÃ©ritage & Polymorphisme de `CONTREPARTIE` (XT)
* **`CONTREPARTIE`** (Classe MÃ¨re Abstraite) : Porte l'identifiant unique universel `id_contrepartie` et le discriminant `type_contrepartie` (`COMPTE_INTERNE`, `BENEFICIAIRE_EXTERNE`, `CAISSE_AGENCE`).
* **`COMPTE`** (SpÃ©cialisation 1) : HÃ©rite de `CONTREPARTIE`. Ajoute `numero_compte`, `solde`, `decouvert_autorise`, `date_ouverture`, `statut`, `id_type_compte`.
* **`BENEFICIAIRE_EXTERNE`** (SpÃ©cialisation 2) : HÃ©rite de `CONTREPARTIE`. Ajoute `iban`, `bic`, `nom_beneficiaire`, `banque_destinataire`.
* **`CAISSE_AGENCE`** (SpÃ©cialisation 3) : HÃ©rite de `CONTREPARTIE`. Ajoute `nom_caisse`, `type_caisse` (`GUICHET_ESPECES`, `GAB_ATM`), `solde_especes`, `id_agence`.

#### Bloc 3 : Typologie des Comptes Bancaires
* **`TYPE_COMPTE`** : RÃ©fÃ©rentiel paramÃ©trable des produits financiers (`id_type_compte`, `libelle`, `taux_remuneration`, `plafond_depot`). Distingue le *Compte Courant*, le *Compte Ã‰pargne RÃ©munÃ©rÃ©*, etc.

#### Bloc 4 : Flux Financiers, Ã‰critures & ImmuabilitÃ©
* **`CANAL`** : ReprÃ©sente le point d'entrÃ©e de l'ordre (`id_canal`, `nom_canal`, `type_canal` : `WEB`, `MOBILE`, `GAB`, `GUICHET`, `TPE`).
* **`TRANSACTION`** : Enveloppe logique de l'Ã©vÃ©nement financier (`id_transaction`, `reference`, `date_heure`, `statut`, `motif`, `id_canal`, `id_agence`, `ip_source`, `user_agent`).
* **`MOUVEMENT`** : Ã‰criture comptable Ã©lÃ©mentaire indivisible (`id_mouvement`, `id_transaction`, `id_contrepartie`, `montant`, `sens`, `date_heure`).
* **Association rÃ©flexive `COMPENSER`** : Relie une transaction de correction Ã  la transaction initiale contestÃ©e.

#### Bloc 5 : MonÃ©tique & Moyens de Paiement
* **`CARTE_BANCAIRE`** : ReprÃ©sente le titre de paiement physique ou virtuel liÃ© Ã  un compte (`id_carte`, `numero_masque`, `date_expiration`, `statut`, `plafond_retrait`, `plafond_paiement`, `id_compte`).

#### Bloc 6 : RÃ©seau Physique & Infrastructure
* **`AGENCE`** : Ã‰tablissement bancaire physique (`id_agence`, `code_agence`, `nom_agence`, `adresse`, `ville`).

---

## 3. ModÃ©lisation Logique des DonnÃ©es (MLD Relationnel & 3NF)

### 3.1. RÃ¨gles de DÃ©rivation Merise vers Relationnel
1. **EntitÃ© Simple** $\rightarrow$ Table avec sa clÃ© primaire naturelle ou technique.
2. **Relation $1\text{--}N$** $\rightarrow$ Migration de la clÃ© primaire du cÃ´tÃ© pÃ¨re vers le cÃ´tÃ© fils sous forme de clÃ© Ã©trangÃ¨re (FK).
3. **Relation $N\text{--}N$ (`TITULARISER`)** $\rightarrow$ Table de jonction dont la clÃ© primaire est composite (`id_client`, `id_compte`, `date_debut`).
4. **HÃ©ritage Exclusif et Total (XT)** : Choix de la stratÃ©gie **Table par Classe (Class-Table Inheritance)**. La table mÃ¨re `CONTREPARTIE` dÃ©tient `id_contrepartie` auto-incrÃ©mentÃ©. Les tables filles (`COMPTE`, `CAISSE_AGENCE`, `BENEFICIAIRE_EXTERNE`) partagent exactement la mÃªme valeur de clÃ© primaire qui est Ã©galement leur clÃ© Ã©trangÃ¨re vers `CONTREPARTIE`.

### 3.2. SchÃ©ma Relationnel Textuel DÃ©taillÃ©

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
    id_transaction_origine INT DEFAULT NULL, -- FK auto-rÃ©fÃ©rentielle COMPENSER
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

### 3.3. DÃ©monstration de la 3Ã¨me Forme Normale (3NF) & BCNF
* **1Ã¨re Forme Normale (1NF)** : Tous les attributs sont atomiques (pas de listes concatÃ©nÃ©es d'adresses ou de numÃ©ros) ; chaque tuple possÃ¨de une clÃ© primaire identifiante unique.
* **2Ã¨me Forme Normale (2NF)** : En 1NF, et tout attribut non-clÃ© dÃ©pend pleinement de la totalitÃ© de la clÃ© primaire. Pour `TITULARISER`, `role_titularite` et `date_fin` dÃ©pendent du triplet `(id_client, id_compte, date_debut)`.
* **3Ã¨me Forme Normale (3NF)** : En 2NF, et aucun attribut non-clÃ© ne dÃ©pend d'un autre attribut non-clÃ© par transitivitÃ© ($X \rightarrow Y \rightarrow Z$).
  - Exemple : L'agence du compte n'induit pas le nom de l'agence dans `COMPTE`. `COMPTE` ne stocke que `id_agence`, Ã©vitant toute anomalie de mise Ã  jour.
* **Forme Normale de Boyce-Codd (BCNF)** : Pour toute dÃ©pendance fonctionnelle Ã©lÃ©mentaire non triviale $X \rightarrow Y$, $X$ est une superclÃ© du schÃ©ma.

---

## 4. ModÃ©lisation Physique & DDL MySQL 8+ (MPD)

L'implÃ©mentation physique garantit la haute performance et la sÃ©curitÃ© des donnÃ©es grÃ¢ce aux clauses MySQL :

```sql
-- Extrait d'intÃ©gritÃ© stricte et indexation (sql/01_schema_sidpef.sql)
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

-- Index stratÃ©giques pour accÃ©lÃ©rer les jointures et requÃªtes d'audit
CREATE INDEX idx_mouvement_contrepartie_date ON MOUVEMENT(id_contrepartie, date_heure);
CREATE INDEX idx_transaction_horodatage ON `TRANSACTION`(date_heure, statut);
CREATE INDEX idx_titulariser_actif ON TITULARISER(id_compte, date_fin);
```

---

## 5. Moteur MÃ©tier en Base de DonnÃ©es (ProcÃ©dures & Triggers)

### 5.1. ProcÃ©dure Transactionnelle `SP_VALIDER_TRANSACTION`
Cette procÃ©dure stockÃ©e est le cÅ“ur battant du rÃ©acteur transactionnel. Elle garantit l'isolation ACID et la partie double.

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

    -- ContrÃ´le du montant strictement positif
    IF p_montant <= 0 THEN
        SET p_statut = 'REJETEE';
        SET p_message = 'Le montant doit Ãªtre strictement supÃ©rieur Ã  zÃ©ro.';
        ROLLBACK;
        LEAVE proc;
    END IF;

    -- VÃ©rification des contreparties et verrouillage pessimiste
    SELECT type_contrepartie INTO v_type_src FROM CONTREPARTIE WHERE id_contrepartie = p_id_source FOR UPDATE;
    SELECT type_contrepartie INTO v_type_dst FROM CONTREPARTIE WHERE id_contrepartie = p_id_destination FOR UPDATE;

    IF v_type_src IS NULL OR v_type_dst IS NULL THEN
        SET p_statut = 'REJETEE';
        SET p_message = 'Contrepartie source ou destination introuvable.';
        ROLLBACK;
        LEAVE proc;
    END IF;

    -- Test de solvabilitÃ© si la source est un compte interne
    IF v_type_src = 'COMPTE_INTERNE' THEN
        SELECT solde, decouvert_autorise, statut 
        INTO v_solde_src, v_decouvert_src, v_statut_src
        FROM COMPTE WHERE id_compte = p_id_source FOR UPDATE;

        IF v_statut_src != 'ACTIF' THEN
            SET p_statut = 'REJETEE';
            SET p_message = 'Le compte Ã©metteur est bloquÃ© ou clÃ´turÃ©.';
            ROLLBACK;
            LEAVE proc;
        END IF;

        IF (v_solde_src + v_decouvert_src) < p_montant THEN
            SET p_statut = 'REJETEE';
            SET p_message = 'Provision insuffisante pour exÃ©cuter le dÃ©bit.';
            ROLLBACK;
            LEAVE proc;
        END IF;
    END IF;

    -- GÃ©nÃ©ration de rÃ©fÃ©rence unique et enregistrement de la transaction
    SET v_ref = CONCAT('TX-', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'), '-', FLOOR(RAND()*9000 + 1000));
    
    INSERT INTO `TRANSACTION` (reference, statut, motif, id_canal, id_agence, ip_source, user_agent)
    VALUES (v_ref, 'VALIDEE', p_motif, p_id_canal, p_id_agence, p_ip, p_ua);
    
    SET p_id_transaction = LAST_INSERT_ID();

    -- Ã‰criture des deux mouvements comptables (Partie Double stricte)
    INSERT INTO MOUVEMENT (id_transaction, id_contrepartie, montant, sens)
    VALUES (p_id_transaction, p_id_source, p_montant, 'DEBIT');

    INSERT INTO MOUVEMENT (id_transaction, id_contrepartie, montant, sens)
    VALUES (p_id_transaction, p_id_destination, p_montant, 'CREDIT');

    -- Mise Ã  jour atomique des soldes internes
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
    SET p_message = 'Virement exÃ©cutÃ© avec succÃ¨s en partie double.';
END proc$$
DELIMITER ;
```

### 5.2. Triggers d'ImmuabilitÃ© Comptable (MySQL Code 1644)
ConformÃ©ment aux normes juridiques bancaires, un mouvement financier ne peut en aucun cas Ãªtre altÃ©rÃ© :

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
