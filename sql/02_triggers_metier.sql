-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE
-- FICHIER : 02_triggers_metier.sql
-- DIALECTE : MySQL 8.0+ / InnoDB
-- OBJECTIF : Procedure stockee de validation comptable et triggers d'immuabilite
-- =============================================================================

USE `banque_centrale_db`;

-- -----------------------------------------------------------------------------
-- TRIGGERS D'IMMUABILITE SUR LA TABLE MOUVEMENT (Piste d'audit bancaire)
-- Toute modification ou suppression d'ecriture comptable est strictement interdite
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS `trg_mouvement_before_update`;
DELIMITER //
CREATE TRIGGER `trg_mouvement_before_update`
BEFORE UPDATE ON `mouvement`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Immuabilite comptable : modification interdite sur les lignes de MOUVEMENT.';
END //
DELIMITER ;

DROP TRIGGER IF EXISTS `trg_mouvement_before_delete`;
DELIMITER //
CREATE TRIGGER `trg_mouvement_before_delete`
BEFORE DELETE ON `mouvement`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Immuabilite comptable : suppression interdite sur la table MOUVEMENT. Utilisez une contre-passation (extourne).';
END //
DELIMITER ;

DROP TRIGGER IF EXISTS `trg_transaction_before_delete`;
DELIMITER //
CREATE TRIGGER `trg_transaction_before_delete`
BEFORE DELETE ON `transaction`
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Piste d audit violee : suppression interdite sur la table TRANSACTION. Utilisez l association COMPENSER.';
END //
DELIMITER ;

-- -----------------------------------------------------------------------------
-- PROCEDURE STOCKEE : SP_VALIDER_TRANSACTION
-- Valide l'equilibre comptable (Total Debits = Total Credits)
-- et met a jour de facon atomique les soldes des COMPTEs concernes
-- -----------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS `SP_VALIDER_TRANSACTION`;
DELIMITER //
CREATE PROCEDURE `SP_VALIDER_TRANSACTION`(
    IN `p_ref_transaction` VARCHAR(30)
)
proc_body: BEGIN
    DECLARE `v_statut`           VARCHAR(15);
    DECLARE `v_nb_mouvements`    INT DEFAULT 0;
    DECLARE `v_total_debit`      DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE `v_total_credit`     DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE `v_deficit_count`    INT DEFAULT 0;

    -- Gestionnaire d'exception SQL : rollback automatique en cas d'erreur
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- 1. Verifier l'existence et verrouiller la transaction en lecture exclusive
    SELECT `statut_trans` INTO `v_statut`
    FROM `transaction`
    WHERE `ref_transaction` = `p_ref_transaction`
    FOR UPDATE;

    IF `v_statut` IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Erreur : Transaction introuvable.';
    END IF;

    IF `v_statut` = 'VALIDEE' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Erreur : La transaction est deja validee.';
    END IF;

    IF `v_statut` <> 'EN_ATTENTE' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Erreur : Seules les transactions au statut EN_ATTENTE peuvent etre validees.';
    END IF;

    -- 2. Agregation et verification de l'equilibre en partie double (RG1 : Sum(D) = Sum(C))
    SELECT
        COUNT(*),
        COALESCE(SUM(CASE WHEN `sens` = 'D' THEN `montant` ELSE 0.00 END), 0.00),
        COALESCE(SUM(CASE WHEN `sens` = 'C' THEN `montant` ELSE 0.00 END), 0.00)
    INTO
        `v_nb_mouvements`,
        `v_total_debit`,
        `v_total_credit`
    FROM `mouvement`
    WHERE `ref_transaction` = `p_ref_transaction`;

    IF `v_nb_mouvements` < 2 THEN
        UPDATE `transaction`
        SET `statut_trans` = 'REJETEE'
        WHERE `ref_transaction` = `p_ref_transaction`;

        COMMIT;

        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rejet comptable : Une transaction en partie double necessite au moins deux mouvements.';
    END IF;

    IF `v_total_debit` <> `v_total_credit` THEN
        UPDATE `transaction`
        SET `statut_trans` = 'REJETEE'
        WHERE `ref_transaction` = `p_ref_transaction`;

        COMMIT;

        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rejet comptable : Desequilibre en partie double (Total Debits <> Total Credits).';
    END IF;

    -- 3. Verifier la solvabilite des comptes internes (respect du decouvert autorise)
    SELECT COUNT(*) INTO `v_deficit_count`
    FROM `compte` c
    JOIN (
        SELECT
            m.`id_contrepartie`,
            SUM(CASE WHEN m.`sens` = 'C' THEN m.`montant` ELSE -m.`montant` END) AS `variation`
        FROM `mouvement` m
        WHERE m.`ref_transaction` = `p_ref_transaction`
        GROUP BY m.`id_contrepartie`
    ) net_mv ON c.`id_contrepartie` = net_mv.`id_contrepartie`
    WHERE (c.`solde` + net_mv.`variation`) < -c.`decouvert_autorise`;

    IF `v_deficit_count` > 0 THEN
        UPDATE `transaction`
        SET `statut_trans` = 'REJETEE'
        WHERE `ref_transaction` = `p_ref_transaction`;

        COMMIT;

        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rejet : Provision insuffisante (depassement du decouvert autorise pour au moins un compte).';
    END IF;

    -- 4. Mise a jour atomique des soldes des comptes internes (COMPTE)
    UPDATE `compte` c
    JOIN (
        SELECT
            m.`id_contrepartie`,
            SUM(CASE WHEN m.`sens` = 'C' THEN m.`montant` ELSE -m.`montant` END) AS `variation`
        FROM `mouvement` m
        WHERE m.`ref_transaction` = `p_ref_transaction`
        GROUP BY m.`id_contrepartie`
    ) net_mv ON c.`id_contrepartie` = net_mv.`id_contrepartie`
    SET c.`solde` = c.`solde` + net_mv.`variation`;

    -- 5. Mise a jour du statut de la transaction a VALIDEE
    UPDATE `transaction`
    SET `statut_trans` = 'VALIDEE'
    WHERE `ref_transaction` = `p_ref_transaction`;

    COMMIT;
END //
DELIMITER ;
