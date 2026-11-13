-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE
-- FICHIER : 04b_explain_performance.sql
-- DIALECTE : MySQL 8.0+ / InnoDB
-- SPRINT 4 : ANALYSE DE PERFORMANCE ET BENCHMARKS EXPLAIN (EXIGENCE 9)
-- RESPONSABLE TECHNIQUE : Yassine Chaouri
-- =============================================================================

USE `banque_centrale_db`;

-- Activation du profilage SQL pour mesurer les micro-temps d'execution
SET profiling = 1;

-- =============================================================================
-- CAS D'ETUDE 1 : RECHERCHE DES TRANSACTIONS PAR HORODATAGE (date_heure)
-- =============================================================================

-- S'assurer que l'index n'existe pas pour demontrer le Full Table Scan
DROP INDEX `idx_transaction_date_heure` ON `transaction`;

-- 1.1. Plan d'execution AVANT creation de l'index
-- Observation attendue : type = 'ALL' (Full Table Scan), aucune cle utilisable
EXPLAIN 
SELECT * 
FROM `transaction` 
WHERE `date_heure` = '2026-11-13 20:33:30';

-- 1.2. Creation de l'index B-Tree cible
CREATE INDEX `idx_transaction_date_heure` ON `transaction` (`date_heure`);

-- 1.3. Plan d'execution APRES creation de l'index
-- Observation attendue : type = 'ref', key = 'idx_transaction_date_heure', rows = 1
EXPLAIN 
SELECT * 
FROM `transaction` 
WHERE `date_heure` = '2026-11-13 20:33:30';


-- =============================================================================
-- CAS D'ETUDE 2 : RECHERCHE CLIENT PAR EMAIL (client.email)
-- =============================================================================

-- S'assurer que l'index n'existe pas pour demontrer le Full Table Scan
DROP INDEX `idx_client_email` ON `client`;

-- 2.1. Plan d'execution AVANT indexation de l'email
-- Observation attendue : type = 'ALL' (Parcours sequentiel de toute la table client)
EXPLAIN 
SELECT * 
FROM `client` 
WHERE `email` = 'yassine.chaouri@banque.ma';

-- 2.2. Creation de l'index B-Tree sur l'adresse email
CREATE INDEX `idx_client_email` ON `client` (`email`);

-- 2.3. Plan d'execution APRES indexation
-- Observation attendue : type = 'ref', key = 'idx_client_email', rows = 1
EXPLAIN 
SELECT * 
FROM `client` 
WHERE `email` = 'yassine.chaouri@banque.ma';


-- =============================================================================
-- CAS D'ETUDE 3 : RECHERCHE DES MOUVEMENTS D'UN COMPTE SUR INTERVALLE DE DATES
-- =============================================================================

-- Plan d'execution exploitant l'index composite (id_contrepartie, date_valeur)
EXPLAIN 
SELECT `id_mouvement`, `sens`, `montant`, `date_valeur`, `ref_transaction`
FROM `mouvement`
WHERE `id_contrepartie` = 1
  AND `date_valeur` >= '2026-01-01';

-- Consultation des statistiques de profilage de sessions
SHOW PROFILES;
