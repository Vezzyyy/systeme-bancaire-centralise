-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
-- SCRIPT : 05_patch_auth.sql
-- SPRINT 7 : GESTION DES IDENTITES, AUTHENTIFICATION JWT ET RBAC
-- RESPONSABLES : Equipe Projet (Yassine, Saad, Hamza, Mouad, Mohamed Amine)
-- =============================================================================
-- Ce script :
-- 1. Ajoute les colonnes mot_de_passe_hash et role a la table client
-- 2. Configure un mot de passe securise hache en bcrypt ("Sidpef2026!") pour les 5 clients
-- 3. Cree un compte Super-Administrateur ("admin@sidpef.ma" / "AdminSidpef2026!")
-- =============================================================================

USE `banque_centrale_db`;

-- 1. ALTER TABLE : Ajout des colonnes de securite (si non presentes)
SET @dbname = DATABASE();
SET @tablename = 'client';
SET @columnname1 = 'mot_de_passe_hash';
SET @columnname2 = 'role';

-- Verification idempotente des colonnes
DROP PROCEDURE IF EXISTS PatchAuthColumns;
DELIMITER $$
CREATE PROCEDURE PatchAuthColumns()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'client' 
          AND COLUMN_NAME = 'mot_de_passe_hash'
    ) THEN
        ALTER TABLE `client` ADD COLUMN `mot_de_passe_hash` VARCHAR(255) NULL AFTER `telephone`;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'client' 
          AND COLUMN_NAME = 'role'
    ) THEN
        ALTER TABLE `client` ADD COLUMN `role` VARCHAR(30) NOT NULL DEFAULT 'CLIENT' AFTER `mot_de_passe_hash`;
    END IF;
END$$
DELIMITER ;

CALL PatchAuthColumns();
DROP PROCEDURE IF EXISTS PatchAuthColumns;

-- 2. MISE A JOUR DES MOTS DE PASSE DES 5 CLIENTS (Mot de passe: Sidpef2026!)
-- Hash Bcrypt : $2b$10$ycSM9fMqmFTLnIIEJGHmjeXRjFq19XWAg0NKQ8TrjeqC/kDvrLOSK
UPDATE `client`
SET `mot_de_passe_hash` = '$2b$10$ycSM9fMqmFTLnIIEJGHmjeXRjFq19XWAg0NKQ8TrjeqC/kDvrLOSK',
    `role` = 'CLIENT'
WHERE `cin` IN ('BE123456', 'BK654321', 'CD789012', 'EE345678', 'AA901234');

-- 3. CREATION DU COMPTE SUPER-ADMINISTRATEUR SIDPEF
-- Identifiants : admin@sidpef.ma / Mot de passe: AdminSidpef2026!
-- Hash Bcrypt : $2b$10$ic4ILWUrrN3e2s7Yl7FiXuwK9HtGgfVb36FjAVlgn33U3OQV/zBvK
INSERT INTO `client` (
    `num_client`, `nom`, `prenom`, `cin`, `date_naissance`, `email`, `telephone`, `mot_de_passe_hash`, `role`
) VALUES (
    99, 'Direction Centrale', 'Administrateur SIDPEF', 'ADMIN001', '1980-01-01', 'admin@sidpef.ma', '+212500000000',
    '$2b$10$ic4ILWUrrN3e2s7Yl7FiXuwK9HtGgfVb36FjAVlgn33U3OQV/zBvK', 'ADMIN'
)
ON DUPLICATE KEY UPDATE
    `nom` = VALUES(`nom`),
    `prenom` = VALUES(`prenom`),
    `email` = VALUES(`email`),
    `mot_de_passe_hash` = VALUES(`mot_de_passe_hash`),
    `role` = VALUES(`role`);

-- Index de performance pour les lookups d'authentification par email ou cin
DROP PROCEDURE IF EXISTS PatchAuthIndex;
DELIMITER $$
CREATE PROCEDURE PatchAuthIndex()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'client' 
          AND INDEX_NAME = 'idx_client_email'
    ) THEN
        CREATE INDEX `idx_client_email` ON `client` (`email`);
    END IF;
END$$
DELIMITER ;

CALL PatchAuthIndex();
DROP PROCEDURE IF EXISTS PatchAuthIndex;

-- Verification finale
SELECT num_client, cin, prenom, nom, email, role, 
       CASE WHEN mot_de_passe_hash IS NOT NULL THEN 'DEFINI (BCRYPT)' ELSE 'ABSENT' END AS statut_mdp
FROM `client`
ORDER BY num_client;
