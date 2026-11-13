-- =============================================================================
-- PROJET : SYSTEME BANCAIRE CENTRALISE
-- FICHIER : 03_donnees_test.sql
-- DIALECTE : MySQL 8.0+ / InnoDB
-- OBJECTIF : Insertion d'un jeu d'essai realiste et execution d'un test de virement
-- =============================================================================

USE `banque_centrale_db`;

-- -----------------------------------------------------------------------------
-- 1. DONNEES DE REFERENCE : TYPES DE COMPTES
-- -----------------------------------------------------------------------------
INSERT INTO `type_compte` (`code_type`, `libelle`, `taux_remuneration`) VALUES
('COURANT', 'Compte Courant Particulier', 0.00),
('EPARGNE', 'Compte sur Carnet Epargne', 2.50),
('PRO',     'Compte Courant Professionnel', 0.00);

-- -----------------------------------------------------------------------------
-- 2. DONNEES DE REFERENCE : CANAUX D'ACCES
-- -----------------------------------------------------------------------------
INSERT INTO `canal` (`code_canal`, `nom_canal`) VALUES
('WEB',     'Portail Web E-Banking'),
('MOBILE',  'Application Mobile Banking'),
('GAB',     'Guichet Automatique de Banque (ATM)'),
('GUICHET', 'Guichet Physique en Agence'),
('TPE',     'Terminal de Paiement Electronique');

-- -----------------------------------------------------------------------------
-- 3. DONNEES DE REFERENCE : TYPES DE TRANSACTIONS
-- -----------------------------------------------------------------------------
INSERT INTO `type_transaction` (`code_type_trans`, `libelle`) VALUES
('VIREMENT',  'Virement de fonds (interne ou externe)'),
('RETRAIT',   'Retrait d especes'),
('DEPOT',     'Depot d especes au guichet'),
('PAIEMENT',  'Paiement par carte bancaire chez commercant'),
('EXTOURNE',  'Annulation comptable compensatoire');

-- -----------------------------------------------------------------------------
-- 4. AGENCES (3 agences)
-- -----------------------------------------------------------------------------
INSERT INTO `agence` (`code_agence`, `nom_agence`, `ville`, `adresse`) VALUES
(1, 'Agence Rabat Hassan',       'Rabat',       '12 Avenue Mohammed V, Quartier Hassan'),
(2, 'Agence Casablanca Maarif',  'Casablanca',  '45 Boulevard Al Massira Al Khadra, Maarif'),
(3, 'Agence Marrakech Gueliz',   'Marrakech',   '78 Avenue Mohammed VI, Gueliz');

-- -----------------------------------------------------------------------------
-- 5. CLIENTS (5 clients)
-- -----------------------------------------------------------------------------
INSERT INTO `client` (`num_client`, `nom`, `prenom`, `cin`, `date_naissance`, `email`, `telephone`) VALUES
(1, 'Chaouri', 'Yassine',        'BE123456', '2001-05-14', 'yassine.chaouri@banque.ma', '+212600112233'),
(2, 'Joudali', 'Saad',           'BK654321', '2000-09-21', 'saad.joudali@banque.ma',   '+212611223344'),
(3, 'Sibous',  'Hamza',          'CD789012', '1999-11-03', 'hamza.sibous@banque.ma',   '+212622334455'),
(4, 'Talibi',  'Mouad',          'EE345678', '2002-02-18', 'mouad.talibi@banque.ma',   '+212633445566'),
(5, 'Aouzagh', 'Mohamed Amine',  'AA901234', '2001-08-30', 'amine.aouzagh@banque.ma',  '+212644556677');

-- -----------------------------------------------------------------------------
-- 6. CONTREPARTIES (Heritage XT : 5 comptes, 1 caisse/GAB, 1 beneficiaire externe)
-- -----------------------------------------------------------------------------
INSERT INTO `contrepartie` (`id_contrepartie`, `type_contrepartie`) VALUES
(1, 'COMPTE'),
(2, 'COMPTE'),
(3, 'COMPTE'),
(4, 'COMPTE'),
(5, 'COMPTE'),
(6, 'CAISSE_AGENCE'),
(7, 'BENEFICIAIRE_EXTERNE');

-- -----------------------------------------------------------------------------
-- 7. COMPTES INTERNES (5 comptes relies aux contreparties 1 a 5)
-- -----------------------------------------------------------------------------
INSERT INTO `compte` (`id_contrepartie`, `solde`, `decouvert_autorise`, `date_ouverture`, `statut`, `code_agence`, `code_type`) VALUES
(1, 15000.00, 2000.00, '2023-01-15', 'ACTIF', 1, 'COURANT'),
(2,  8500.00, 1000.00, '2023-02-20', 'ACTIF', 1, 'COURANT'),
(3, 24000.00, 5000.00, '2022-11-10', 'ACTIF', 2, 'COURANT'),
(4, 50000.00,    0.00, '2023-04-05', 'ACTIF', 2, 'EPARGNE'),
(5, 12000.00, 1500.00, '2023-06-12', 'ACTIF', 3, 'COURANT');

-- -----------------------------------------------------------------------------
-- 8. TITULARISATION (Lien Client <-> Compte)
-- -----------------------------------------------------------------------------
INSERT INTO `titulariser` (`role`, `date_debut`, `date_fin`, `id_contrepartie_compte`, `num_client`) VALUES
('PRINCIPAL', '2023-01-15', NULL, 1, 1),
('PRINCIPAL', '2023-02-20', NULL, 2, 2),
('PRINCIPAL', '2022-11-10', NULL, 3, 3),
('PRINCIPAL', '2023-04-05', NULL, 4, 4),
('PRINCIPAL', '2023-06-12', NULL, 5, 5);

-- -----------------------------------------------------------------------------
-- 9. CAISSE / GAB (1 ATM rattache a l'agence Rabat Hassan)
-- -----------------------------------------------------------------------------
INSERT INTO `caisse_agence` (`id_contrepartie`, `libelle_caisse`, `code_agence`) VALUES
(6, 'Caisse GAB Hassan 01 (ATM)', 1);

-- -----------------------------------------------------------------------------
-- 10. BENEFICIAIRE EXTERNE (1 beneficiaire interbancaire avec IBAN/BIC)
-- -----------------------------------------------------------------------------
INSERT INTO `beneficiaire_externe` (`id_contrepartie`, `iban`, `bic`, `nom_beneficiaire`) VALUES
(7, 'MA64011512345678901234567890', 'BMAAMAMC', 'Societe Marocaine de Distribution SARL');

-- -----------------------------------------------------------------------------
-- 11. CARTES BANCAIRES (Exemples)
-- -----------------------------------------------------------------------------
INSERT INTO `carte_bancaire` (`num_carte`, `date_expiration`, `statut_carte`, `plafond_paiement`, `plafond_retrait`, `id_contrepartie_compte`, `num_client`) VALUES
('4152890011223344', '2027-12-31', 'ACTIVE', 10000.00, 3000.00, 1, 1),
('4152890055667788', '2028-06-30', 'ACTIVE',  8000.00, 2000.00, 2, 2);

-- =============================================================================
-- SCENARIO DE TEST : VIREMENT INTERNE DE 2 500.00 MAD DE COMPTE 1 VERS COMPTE 2
-- =============================================================================

-- A. Consultation de l'etat des soldes AVANT le virement
SELECT
    c.`id_contrepartie` AS `id_compte`,
    CONCAT(cl.`prenom`, ' ', cl.`nom`) AS `titulaire`,
    c.`solde` AS `solde_avant`,
    c.`decouvert_autorise`
FROM `compte` c
JOIN `titulariser` t ON c.`id_contrepartie` = t.`id_contrepartie_compte`
JOIN `client` cl     ON t.`num_client` = cl.`num_client`
WHERE c.`id_contrepartie` IN (1, 2)
ORDER BY c.`id_contrepartie`;

-- B. Creation de l'evenement metier (TRANSACTION au statut EN_ATTENTE)
INSERT INTO `transaction` (
    `ref_transaction`,
    `date_heure`,
    `statut_trans`,
    `ip_source`,
    `device_fingerprint`,
    `code_type_trans`,
    `code_canal`
) VALUES (
    'TX-2026-VIR-001',
    NOW(),
    'EN_ATTENTE',
    '196.200.15.42',
    'fp_iphone15_pro_yassine',
    'VIREMENT',
    'MOBILE'
);

-- C. Generation des ecritures comptables en partie double (2 MOUVEMENTs)
-- 1. Debit de 2 500.00 MAD sur le compte emetteur (id_contrepartie = 1)
INSERT INTO `mouvement` (
    `sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`
) VALUES (
    'D', 2500.00, CURDATE(), 'MAD', 'TX-2026-VIR-001', 1
);

-- 2. Credit de 2 500.00 MAD sur le compte recepteur (id_contrepartie = 2)
INSERT INTO `mouvement` (
    `sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`
) VALUES (
    'C', 2500.00, CURDATE(), 'MAD', 'TX-2026-VIR-001', 2
);

-- D. Execution de la procedure stockee de validation
CALL `SP_VALIDER_TRANSACTION`('TX-2026-VIR-001');

-- E. Consultation de l'etat des soldes APRES le virement (Compte 1 : 12 500 | Compte 2 : 11 000)
SELECT
    c.`id_contrepartie` AS `id_compte`,
    CONCAT(cl.`prenom`, ' ', cl.`nom`) AS `titulaire`,
    c.`solde` AS `solde_apres`,
    c.`decouvert_autorise`
FROM `compte` c
JOIN `titulariser` t ON c.`id_contrepartie` = t.`id_contrepartie_compte`
JOIN `client` cl     ON t.`num_client` = cl.`num_client`
WHERE c.`id_contrepartie` IN (1, 2)
ORDER BY c.`id_contrepartie`;

-- F. Verification du statut final de la transaction
SELECT
    `ref_transaction`,
    `date_heure`,
    `statut_trans`,
    `code_type_trans`,
    `code_canal`
FROM `transaction`
WHERE `ref_transaction` = 'TX-2026-VIR-001';

-- G. Verification des ecritures comptables associees
SELECT
    `id_mouvement`,
    `sens`,
    `montant`,
    `devise`,
    `id_contrepartie`,
    `ref_transaction`
FROM `mouvement`
WHERE `ref_transaction` = 'TX-2026-VIR-001';

-- =============================================================================
-- ENRICHISSEMENT DU JEU D'ESSAI POUR LES REQUETES ANALYTIQUES (SPRINT 4)
-- =============================================================================

-- 1. Transaction en attente (Virement Web de 1 000 MAD entre C3 et C4)
INSERT INTO `transaction` (`ref_transaction`, `date_heure`, `statut_trans`, `ip_source`, `code_type_trans`, `code_canal`)
VALUES ('TX-2026-ATT-002', NOW(), 'EN_ATTENTE', '196.200.15.50', 'VIREMENT', 'WEB');

INSERT INTO `mouvement` (`sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`)
VALUES ('D', 1000.00, CURDATE(), 'MAD', 'TX-2026-ATT-002', 3),
       ('C', 1000.00, CURDATE(), 'MAD', 'TX-2026-ATT-002', 4);

-- 2. Transaction rejetee (Tentative de virement avec montant excessif)
INSERT INTO `transaction` (`ref_transaction`, `date_heure`, `statut_trans`, `ip_source`, `code_type_trans`, `code_canal`)
VALUES ('TX-2026-REJ-003', NOW(), 'REJETEE', '196.200.15.75', 'VIREMENT', 'MOBILE');

INSERT INTO `mouvement` (`sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`)
VALUES ('D', 999999.00, CURDATE(), 'MAD', 'TX-2026-REJ-003', 2),
       ('C', 999999.00, CURDATE(), 'MAD', 'TX-2026-REJ-003', 5);

-- 3. Depot d especes au guichet physique (Compte 1 : +5 000 MAD, Caisse 6 : -5 000 MAD)
INSERT INTO `transaction` (`ref_transaction`, `date_heure`, `statut_trans`, `code_type_trans`, `code_canal`)
VALUES ('TX-2026-DEP-004', DATE_SUB(NOW(), INTERVAL 2 HOUR), 'EN_ATTENTE', 'DEPOT', 'GUICHET');

INSERT INTO `mouvement` (`sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`)
VALUES ('D', 5000.00, CURDATE(), 'MAD', 'TX-2026-DEP-004', 6),
       ('C', 5000.00, CURDATE(), 'MAD', 'TX-2026-DEP-004', 1);

CALL `SP_VALIDER_TRANSACTION`('TX-2026-DEP-004');

-- 4. Retrait d especes au GAB par carte (Compte 1 : -800 MAD, Caisse 6 : +800 MAD)
INSERT INTO `transaction` (`ref_transaction`, `date_heure`, `statut_trans`, `code_type_trans`, `code_canal`, `num_carte`)
VALUES ('TX-2026-RET-005', DATE_SUB(NOW(), INTERVAL 1 HOUR), 'EN_ATTENTE', 'RETRAIT', 'GAB', '4152890011223344');

INSERT INTO `mouvement` (`sens`, `montant`, `date_valeur`, `devise`, `ref_transaction`, `id_contrepartie`)
VALUES ('D', 800.00, CURDATE(), 'MAD', 'TX-2026-RET-005', 1),
       ('C', 800.00, CURDATE(), 'MAD', 'TX-2026-RET-005', 6);

CALL `SP_VALIDER_TRANSACTION`('TX-2026-RET-005');


-- -----------------------------------------------------------------------------
-- DEMONSTRATION DE LA SECURITE D'IMMUABILITE (Optionnel)
-- Si vous tentez de modifier ou supprimer un mouvement, les triggers declenchent une erreur :
--
-- UPDATE `mouvement` SET `montant` = 9999.00 WHERE `id_mouvement` = 1;
-- -> ERROR 1644 (45000): Immuabilite comptable : modification interdite sur les lignes de MOUVEMENT.
--
-- DELETE FROM `mouvement` WHERE `id_mouvement` = 1;
-- -> ERROR 1644 (45000): Immuabilite comptable : suppression interdite sur la table MOUVEMENT.
-- -----------------------------------------------------------------------------
