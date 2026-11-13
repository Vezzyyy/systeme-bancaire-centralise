-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE
-- FICHIER : 01_schema_sidpef.sql
-- DIALECTE : MySQL 8.0+ / InnoDB
-- OBJECTIF : DDL de creation des tables, contraintes d'integrite et index
-- =============================================================================

DROP DATABASE IF EXISTS `banque_centrale_db`;
CREATE DATABASE `banque_centrale_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `banque_centrale_db`;

-- -----------------------------------------------------------------------------
-- 1. TABLE : AGENCE
-- -----------------------------------------------------------------------------
CREATE TABLE `agence` (
    `code_agence` INT AUTO_INCREMENT,
    `nom_agence`  VARCHAR(100) NOT NULL,
    `ville`       VARCHAR(60)  NOT NULL,
    `adresse`     VARCHAR(200) NULL,
    CONSTRAINT `pk_agence` PRIMARY KEY (`code_agence`)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 2. TABLE : TYPE_COMPTE
-- -----------------------------------------------------------------------------
CREATE TABLE `type_compte` (
    `code_type`         VARCHAR(10),
    `libelle`           VARCHAR(60)    NOT NULL,
    `taux_remuneration` DECIMAL(5, 2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT `pk_type_compte` PRIMARY KEY (`code_type`),
    CONSTRAINT `chk_type_compte_taux` CHECK (`taux_remuneration` >= 0.00)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 3. TABLE : CLIENT
-- -----------------------------------------------------------------------------
CREATE TABLE `client` (
    `num_client`     INT AUTO_INCREMENT,
    `nom`            VARCHAR(60)  NOT NULL,
    `prenom`         VARCHAR(60)  NOT NULL,
    `cin`            VARCHAR(20)  NOT NULL,
    `date_naissance` DATE         NULL,
    `email`          VARCHAR(128) NULL,
    `telephone`      VARCHAR(20)  NULL,
    CONSTRAINT `pk_client` PRIMARY KEY (`num_client`),
    CONSTRAINT `uq_client_cin` UNIQUE (`cin`)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 4. TABLE : CONTREPARTIE (Entite mere de l'heritage par classe XT)
-- -----------------------------------------------------------------------------
CREATE TABLE `contrepartie` (
    `id_contrepartie`   INT AUTO_INCREMENT,
    `type_contrepartie` VARCHAR(20) NOT NULL,
    CONSTRAINT `pk_contrepartie` PRIMARY KEY (`id_contrepartie`),
    CONSTRAINT `chk_contrepartie_type` CHECK (
        `type_contrepartie` IN ('COMPTE', 'BENEFICIAIRE_EXTERNE', 'CAISSE_AGENCE')
    )
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 5. TABLE : CAISSE_AGENCE (Sous-type CONTREPARTIE)
-- -----------------------------------------------------------------------------
CREATE TABLE `caisse_agence` (
    `id_contrepartie` INT,
    `libelle_caisse`  VARCHAR(60) NOT NULL,
    `code_agence`     INT         NOT NULL,
    CONSTRAINT `pk_caisse_agence` PRIMARY KEY (`id_contrepartie`),
    CONSTRAINT `fk_caisse_contrepartie`
        FOREIGN KEY (`id_contrepartie`) REFERENCES `contrepartie` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_caisse_agence`
        FOREIGN KEY (`code_agence`) REFERENCES `agence` (`code_agence`)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 6. TABLE : BENEFICIAIRE_EXTERNE (Sous-type CONTREPARTIE)
-- -----------------------------------------------------------------------------
CREATE TABLE `beneficiaire_externe` (
    `id_contrepartie`  INT,
    `iban`             VARCHAR(34)  NOT NULL,
    `bic`              VARCHAR(11)  NULL,
    `nom_beneficiaire` VARCHAR(100) NOT NULL,
    CONSTRAINT `pk_beneficiaire_externe` PRIMARY KEY (`id_contrepartie`),
    CONSTRAINT `uq_beneficiaire_iban` UNIQUE (`iban`),
    CONSTRAINT `fk_beneficiaire_contrepartie`
        FOREIGN KEY (`id_contrepartie`) REFERENCES `contrepartie` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 7. TABLE : COMPTE (Sous-type CONTREPARTIE)
-- -----------------------------------------------------------------------------
CREATE TABLE `compte` (
    `id_contrepartie`    INT,
    `solde`              DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    `decouvert_autorise` DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    `date_ouverture`     DATE           NOT NULL,
    `statut`             VARCHAR(15)    NOT NULL DEFAULT 'ACTIF',
    `code_agence`        INT            NOT NULL,
    `code_type`          VARCHAR(10)    NOT NULL,
    CONSTRAINT `pk_compte` PRIMARY KEY (`id_contrepartie`),
    CONSTRAINT `fk_compte_contrepartie`
        FOREIGN KEY (`id_contrepartie`) REFERENCES `contrepartie` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_compte_agence`
        FOREIGN KEY (`code_agence`) REFERENCES `agence` (`code_agence`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_compte_type`
        FOREIGN KEY (`code_type`) REFERENCES `type_compte` (`code_type`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_compte_decouvert_positif` CHECK (`decouvert_autorise` >= 0.00),
    CONSTRAINT `chk_compte_solde_decouvert` CHECK (`solde` >= -`decouvert_autorise`),
    CONSTRAINT `chk_compte_statut` CHECK (`statut` IN ('ACTIF', 'BLOQUE', 'CLOTURE'))
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 8. TABLE : TITULARISER
-- -----------------------------------------------------------------------------
CREATE TABLE `titulariser` (
    `num_titularite`         INT AUTO_INCREMENT,
    `role`                   VARCHAR(20) NOT NULL DEFAULT 'PRINCIPAL',
    `date_debut`             DATE        NOT NULL,
    `date_fin`               DATE        NULL,
    `id_contrepartie_compte` INT         NOT NULL,
    `num_client`             INT         NOT NULL,
    CONSTRAINT `pk_titulariser` PRIMARY KEY (`num_titularite`),
    CONSTRAINT `fk_titulariser_compte`
        FOREIGN KEY (`id_contrepartie_compte`) REFERENCES `compte` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_titulariser_client`
        FOREIGN KEY (`num_client`) REFERENCES `client` (`num_client`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_titulariser_dates` CHECK (`date_fin` IS NULL OR `date_fin` >= `date_debut`),
    CONSTRAINT `chk_titulariser_role` CHECK (`role` IN ('PRINCIPAL', 'COTITULAIRE', 'MANDATAIRE'))
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 9. TABLE : CARTE_BANCAIRE
-- -----------------------------------------------------------------------------
CREATE TABLE `carte_bancaire` (
    `num_carte`              VARCHAR(19),
    `date_expiration`        DATE           NOT NULL,
    `statut_carte`           VARCHAR(15)    NOT NULL DEFAULT 'ACTIVE',
    `plafond_paiement`       DECIMAL(12, 2) NOT NULL DEFAULT 5000.00,
    `plafond_retrait`        DECIMAL(12, 2) NOT NULL DEFAULT 2000.00,
    `id_contrepartie_compte` INT            NOT NULL,
    `num_client`             INT            NOT NULL,
    CONSTRAINT `pk_carte_bancaire` PRIMARY KEY (`num_carte`),
    CONSTRAINT `fk_carte_compte`
        FOREIGN KEY (`id_contrepartie_compte`) REFERENCES `compte` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_carte_client`
        FOREIGN KEY (`num_client`) REFERENCES `client` (`num_client`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_carte_plafond_paiement` CHECK (`plafond_paiement` >= 0.00),
    CONSTRAINT `chk_carte_plafond_retrait` CHECK (`plafond_retrait` >= 0.00),
    CONSTRAINT `chk_carte_statut` CHECK (`statut_carte` IN ('ACTIVE', 'BLOC_TEMPORAIRE', 'OPPOSEE', 'EXPIREE'))
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 10. TABLE : CANAL
-- -----------------------------------------------------------------------------
CREATE TABLE `canal` (
    `code_canal` VARCHAR(10),
    `nom_canal`  VARCHAR(60) NOT NULL,
    CONSTRAINT `pk_canal` PRIMARY KEY (`code_canal`)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 11. TABLE : TYPE_TRANSACTION
-- -----------------------------------------------------------------------------
CREATE TABLE `type_transaction` (
    `code_type_trans` VARCHAR(10),
    `libelle`         VARCHAR(60) NOT NULL,
    CONSTRAINT `pk_type_transaction` PRIMARY KEY (`code_type_trans`)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 12. TABLE : TRANSACTION (Mot reserve MySQL -> nom echappe avec backticks)
-- -----------------------------------------------------------------------------
CREATE TABLE `transaction` (
    `ref_transaction`        VARCHAR(30),
    `date_heure`             TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `statut_trans`           VARCHAR(15) NOT NULL DEFAULT 'EN_ATTENTE',
    `ip_source`              VARCHAR(45) NULL,
    `device_fingerprint`     VARCHAR(128) NULL,
    `code_type_trans`        VARCHAR(10) NOT NULL,
    `code_canal`             VARCHAR(10) NOT NULL,
    `num_carte`              VARCHAR(19) NULL,
    `ref_transaction_annulee` VARCHAR(30) NULL,
    CONSTRAINT `pk_transaction` PRIMARY KEY (`ref_transaction`),
    CONSTRAINT `fk_transaction_type`
        FOREIGN KEY (`code_type_trans`) REFERENCES `type_transaction` (`code_type_trans`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_transaction_canal`
        FOREIGN KEY (`code_canal`) REFERENCES `canal` (`code_canal`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_transaction_carte`
        FOREIGN KEY (`num_carte`) REFERENCES `carte_bancaire` (`num_carte`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_transaction_compenser`
        FOREIGN KEY (`ref_transaction_annulee`) REFERENCES `transaction` (`ref_transaction`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_transaction_statut` CHECK (`statut_trans` IN ('EN_ATTENTE', 'VALIDEE', 'REJETEE', 'ANNULEE'))
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- 13. TABLE : MOUVEMENT (Ecritures comptables en partie double)
-- -----------------------------------------------------------------------------
CREATE TABLE `mouvement` (
    `id_mouvement`    BIGINT AUTO_INCREMENT,
    `sens`            CHAR(1)        NOT NULL,
    `montant`         DECIMAL(15, 2) NOT NULL,
    `date_valeur`     DATE           NOT NULL,
    `devise`          CHAR(3)        NOT NULL DEFAULT 'MAD',
    `ref_transaction` VARCHAR(30)    NOT NULL,
    `id_contrepartie` INT            NOT NULL,
    CONSTRAINT `pk_mouvement` PRIMARY KEY (`id_mouvement`),
    CONSTRAINT `fk_mouvement_transaction`
        FOREIGN KEY (`ref_transaction`) REFERENCES `transaction` (`ref_transaction`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_mouvement_contrepartie`
        FOREIGN KEY (`id_contrepartie`) REFERENCES `contrepartie` (`id_contrepartie`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_mouvement_sens` CHECK (`sens` IN ('D', 'C')),
    CONSTRAINT `chk_mouvement_montant` CHECK (`montant` > 0.00)
) ENGINE=InnoDB;

-- =============================================================================
-- INDEX POUR L'OPTIMISATION DES REQUETES ET JOINTURES FREQUENTES
-- =============================================================================

CREATE INDEX `idx_client_cin` ON `client` (`cin`);
CREATE INDEX `idx_caisse_agence_code_agence` ON `caisse_agence` (`code_agence`);
CREATE INDEX `idx_compte_code_agence` ON `compte` (`code_agence`);
CREATE INDEX `idx_compte_code_type` ON `compte` (`code_type`);
CREATE INDEX `idx_titulariser_compte` ON `titulariser` (`id_contrepartie_compte`);
CREATE INDEX `idx_titulariser_client` ON `titulariser` (`num_client`);
CREATE INDEX `idx_carte_compte` ON `carte_bancaire` (`id_contrepartie_compte`);
CREATE INDEX `idx_carte_client` ON `carte_bancaire` (`num_client`);
CREATE INDEX `idx_transaction_type` ON `transaction` (`code_type_trans`);
CREATE INDEX `idx_transaction_canal` ON `transaction` (`code_canal`);
CREATE INDEX `idx_transaction_carte` ON `transaction` (`num_carte`);
CREATE INDEX `idx_transaction_annulee` ON `transaction` (`ref_transaction_annulee`);
CREATE INDEX `idx_mouvement_transaction` ON `mouvement` (`ref_transaction`);
CREATE INDEX `idx_mouvement_id_contrepartie` ON `mouvement` (`id_contrepartie`);
CREATE INDEX `idx_mouvement_date_valeur` ON `mouvement` (`date_valeur`);
