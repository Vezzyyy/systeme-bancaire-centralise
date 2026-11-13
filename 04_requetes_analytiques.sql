-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE
-- FICHIER : 04_requetes_analytiques.sql
-- DIALECTE : MySQL 8.0+ / InnoDB
-- SPRINT 4 : REQUETAGE AVANCE ET ANALYSE D'INDEXATION (EXIGENCES 8 & 9)
-- RESPONSABLE DU SPRINT : Mouad Talibi & Equipe
-- =============================================================================

USE `banque_centrale_db`;

-- =============================================================================
-- PARTIE 1 : EXIGENCE 8 — REQUETES METIER PERTINENTES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. SELECTION & FILTRAGE : Transactions en attente ou rejetees aujourd'hui
-- Objectif : Dashboard des operations necessitant une intervention ou verification
-- -----------------------------------------------------------------------------
SELECT 
    t.`ref_transaction`,
    t.`date_heure`,
    t.`statut_trans`,
    tt.`libelle` AS `type_transaction`,
    c.`nom_canal` AS `canal`,
    t.`ip_source`,
    COALESCE(SUM(m.`montant`) / 2, 0.00) AS `montant_operation`
FROM `transaction` t
JOIN `type_transaction` tt ON t.`code_type_trans` = tt.`code_type_trans`
JOIN `canal` c            ON t.`code_canal` = c.`code_canal`
LEFT JOIN `mouvement` m    ON t.`ref_transaction` = m.`ref_transaction`
WHERE t.`statut_trans` IN ('EN_ATTENTE', 'REJETEE')
  AND DATE(t.`date_heure`) = CURDATE()
GROUP BY 
    t.`ref_transaction`, 
    t.`date_heure`, 
    t.`statut_trans`, 
    tt.`libelle`, 
    c.`nom_canal`, 
    t.`ip_source`
ORDER BY t.`date_heure` DESC;

-- -----------------------------------------------------------------------------
-- 2. JOINTURES COMPLEXES : Vue 360° et historique complet d'un client
-- Objectif : Consolider les comptes, cartes liees et mouvements recents (ex: Yassine Chaouri)
-- -----------------------------------------------------------------------------
SELECT 
    cl.`num_client`,
    CONCAT(cl.`prenom`, ' ', cl.`nom`) AS `client_nom_complet`,
    cl.`cin`,
    ag.`nom_agence`,
    cp.`id_contrepartie` AS `num_compte`,
    tc.`libelle` AS `type_compte`,
    cp.`solde`,
    cp.`decouvert_autorise`,
    tit.`role` AS `role_titulaire`,
    COALESCE(cb.`num_carte`, 'Aucune') AS `num_carte`,
    COALESCE(cb.`statut_carte`, 'N/A') AS `statut_carte`,
    m.`id_mouvement`,
    m.`date_valeur`,
    m.`sens`,
    m.`montant`,
    tt.`libelle` AS `nature_operation`
FROM `client` cl
JOIN `titulariser` tit        ON cl.`num_client` = tit.`num_client`
JOIN `compte` cp             ON tit.`id_contrepartie_compte` = cp.`id_contrepartie`
JOIN `agence` ag             ON cp.`code_agence` = ag.`code_agence`
JOIN `type_compte` tc        ON cp.`code_type` = tc.`code_type`
LEFT JOIN `carte_bancaire` cb ON cp.`id_contrepartie` = cb.`id_contrepartie_compte` 
                             AND cl.`num_client` = cb.`num_client`
LEFT JOIN `mouvement` m      ON cp.`id_contrepartie` = m.`id_contrepartie`
LEFT JOIN `transaction` t     ON m.`ref_transaction` = t.`ref_transaction`
LEFT JOIN `type_transaction` tt ON t.`code_type_trans` = tt.`code_type_trans`
WHERE cl.`cin` = 'BE123456'
ORDER BY m.`date_valeur` DESC, m.`id_mouvement` DESC;

-- -----------------------------------------------------------------------------
-- 3. AGREGATION (GROUP BY) : Total des depots et retraits par agence (mois en cours)
-- Objectif : Suivi de la liquidite physique et flux de caisse par point de vente
-- -----------------------------------------------------------------------------
SELECT 
    ag.`code_agence`,
    ag.`nom_agence`,
    ag.`ville`,
    COUNT(DISTINCT t.`ref_transaction`) AS `nb_operations_especes`,
    COALESCE(SUM(CASE WHEN tt.`code_type_trans` = 'DEPOT'   AND m.`sens` = 'D' THEN m.`montant` ELSE 0.00 END), 0.00) AS `total_depots_caisse`,
    COALESCE(SUM(CASE WHEN tt.`code_type_trans` = 'RETRAIT' AND m.`sens` = 'C' THEN m.`montant` ELSE 0.00 END), 0.00) AS `total_retraits_caisse`,
    COALESCE(SUM(CASE WHEN tt.`code_type_trans` = 'DEPOT'   AND m.`sens` = 'D' THEN m.`montant` ELSE 0.00 END), 0.00) -
    COALESCE(SUM(CASE WHEN tt.`code_type_trans` = 'RETRAIT' AND m.`sens` = 'C' THEN m.`montant` ELSE 0.00 END), 0.00) AS `flux_net_caisse_agence`
FROM `agence` ag
JOIN `caisse_agence` ca ON ag.`code_agence` = ca.`code_agence`
LEFT JOIN `mouvement` m   ON ca.`id_contrepartie` = m.`id_contrepartie`
LEFT JOIN `transaction` t ON m.`ref_transaction` = t.`ref_transaction` 
                          AND t.`statut_trans` = 'VALIDEE'
                          AND YEAR(t.`date_heure`) = YEAR(CURDATE())
                          AND MONTH(t.`date_heure`) = MONTH(CURDATE())
LEFT JOIN `type_transaction` tt ON t.`code_type_trans` = tt.`code_type_trans`
GROUP BY ag.`code_agence`, ag.`nom_agence`, ag.`ville`
ORDER BY `flux_net_caisse_agence` DESC;

-- -----------------------------------------------------------------------------
-- 4. SOUS-REQUETE : Clients dont le solde total consolide depasse la moyenne nationale
-- Objectif : Segmentation client patrimoniale / Banque Privée
-- -----------------------------------------------------------------------------
SELECT 
    cl.`num_client`,
    CONCAT(cl.`prenom`, ' ', cl.`nom`) AS `client_nom`,
    cl.`cin`,
    cl.`email`,
    COUNT(cp.`id_contrepartie`) AS `nb_comptes_actifs`,
    SUM(cp.`solde`) AS `solde_total_consolide`,
    ROUND((SELECT AVG(`solde`) FROM `compte`), 2) AS `moyenne_nationale_banque`
FROM `client` cl
JOIN `titulariser` tit ON cl.`num_client` = tit.`num_client`
JOIN `compte` cp      ON tit.`id_contrepartie_compte` = cp.`id_contrepartie`
GROUP BY cl.`num_client`, cl.`nom`, cl.`prenom`, cl.`cin`, cl.`email`
HAVING SUM(cp.`solde`) > (
    -- Sous-requete scalaire calculant le solde moyen par compte
    SELECT AVG(`solde`) FROM `compte`
)
ORDER BY `solde_total_consolide` DESC;

-- -----------------------------------------------------------------------------
-- 5. REQUETE ELABOREE : Releve de compte chronologique avec Window Function (SUM OVER)
-- Objectif : Reconstitution comptable exacte ligne a ligne du solde progressif
-- -----------------------------------------------------------------------------
SELECT 
    m.`id_mouvement`,
    t.`date_heure`,
    m.`date_valeur`,
    t.`ref_transaction`,
    tt.`libelle` AS `libelle_operation`,
    cn.`nom_canal` AS `canal`,
    CASE WHEN m.`sens` = 'D' THEN m.`montant` ELSE NULL END AS `debit`,
    CASE WHEN m.`sens` = 'C' THEN m.`montant` ELSE NULL END AS `credit`,
    -- Fonction de fenetrage analytique MySQL 8+
    SUM(CASE WHEN m.`sens` = 'C' THEN m.`montant` ELSE -m.`montant` END) 
        OVER (
            PARTITION BY m.`id_contrepartie` 
            ORDER BY m.`id_mouvement` ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS `solde_progressif_mouvements`
FROM `mouvement` m
JOIN `transaction` t        ON m.`ref_transaction` = t.`ref_transaction`
JOIN `type_transaction` tt ON t.`code_type_trans` = tt.`code_type_trans`
JOIN `canal` cn            ON t.`code_canal` = cn.`code_canal`
WHERE m.`id_contrepartie` = 1
  AND t.`statut_trans` = 'VALIDEE'
ORDER BY m.`id_mouvement` ASC;


-- =============================================================================
-- PARTIE 2 : EXIGENCE 9 — PREUVE D'INDEXATION ET ANALYSE DE PERFORMANCE (EXPLAIN)
-- =============================================================================

-- Cas d'etude : Recherche des transactions par horodatage (dateHeure)

-- -----------------------------------------------------------------------------
-- ETAPE A : Execution de EXPLAIN AVANT indexation
-- Resultat attendu : type = 'ALL' (Full Table Scan), key = NULL, possible_keys = NULL
-- -----------------------------------------------------------------------------
EXPLAIN 
SELECT * 
FROM `transaction` 
WHERE `date_heure` = '2026-11-13 20:33:30';

-- -----------------------------------------------------------------------------
-- ETAPE B : Creation de l'index B-Tree cible
-- -----------------------------------------------------------------------------
CREATE INDEX `idx_transaction_date_heure` ON `transaction` (`date_heure`);

-- -----------------------------------------------------------------------------
-- ETAPE C : Execution de EXPLAIN APRES indexation
-- Resultat attendu : type = 'ref', key = 'idx_transaction_date_heure', rows = 1
-- -----------------------------------------------------------------------------
EXPLAIN 
SELECT * 
FROM `transaction` 
WHERE `date_heure` = '2026-11-13 20:33:30';


-- Demonstration complementaire : Recherche client par Email
-- 1. Avant index : Full Scan (type: ALL)
EXPLAIN 
SELECT * 
FROM `client` 
WHERE `email` = 'yassine.chaouri@banque.ma';

-- 2. Creation de l'index
CREATE INDEX `idx_client_email` ON `client` (`email`);

-- 3. Apres index : Recherche directe (type: ref)
EXPLAIN 
SELECT * 
FROM `client` 
WHERE `email` = 'yassine.chaouri@banque.ma';
