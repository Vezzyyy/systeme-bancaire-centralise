# Système Bancaire Centralisé - Conception & Modélisation de Base de Données

Ce dépôt contient l'analyse, la conception conceptuelle, la modélisation logique et les spécifications techniques de la base de données d'un **Système Bancaire Centralisé**. Le projet s'appuie sur la méthode **Merise** et respecte les normes bancaires fondamentales (traçabilité, comptabilité en partie double, immuabilité des écritures).

---

## 👥 Équipe du Projet

- **Yassine Chaouri** ([@Vezzyyy](https://github.com/Vezzyyy))
- **Saad Joudali** ([@joudali-saad](https://github.com/joudali-saad))
- **Hamza Sibous** ([@hamzasibous](https://github.com/hamzasibous))
- **Mouad Talibi** ([@MouadWork](https://github.com/MouadWork))
- **Mohamed Amine Aouzagh** ([@MAminezzz](https://github.com/MAminezzz))

---

## 📌 Architecture & Principes Métier Clés

1. **Comptabilité en partie double** :
   - Toute opération financière est représentée par une `TRANSACTION` décomposée en 1 à $N$ lignes comptables (`MOUVEMENT`).
   - Règle fondamentale : $\sum \text{Débits} = \sum \text{Crédits}$ pour chaque transaction validée.
2. **Polymorphisme et Héritage (XT)** :
   - L'entité abstraite `CONTREPARTIE` permet d'imputer des mouvements de manière homogène vers :
     - Des comptes bancaires internes (`COMPTE`).
     - Des bénéficiaires externes via IBAN / BIC (`BENEFICIAIRE_EXTERNE`).
     - Les caisses physiques des agences pour les opérations en espèces (`CAISSE_AGENCE`).
3. **Découplage de la titularité (`TITULARITE`)** :
   - Gestion avancée des comptes joints, mandats et procurations avec historisation temporelle (`dateDebut`, `dateFin`, `role`).
4. **Immuabilité et Piste d'audit (`COMPENSER`)** :
   - Aucune transaction bancaire validée n'est supprimée de la base de données.
   - Les annulations sont modélisées par une association réflexive reliant la transaction erronée à une transaction d'extourne de sens inverse.
5. **Gestion multi-canal et monétique** :
   - Traçabilité du canal d'initiation (`CANAL` : mobile, web, guichet, GAB/DAB, TPE).
   - Gestion des cartes bancaires (`CARTE_BANCAIRE`) avec plafonds distincts de retrait et de paiement.

---

## 🗂️ Documents & Scripts du Projet

- **Guide d'Installation & Prise en Main** : [`TUTORIEL_INSTALLATION.md`](./TUTORIEL_INSTALLATION.md) — Guide pas-à-pas pour cloner, charger la base MySQL et lancer l'application en 5 minutes.
- **Rapport de Projet Détaillé** : [`RAPPORT_PROJET_COMPLET.md`](./RAPPORT_PROJET_COMPLET.md) — Documentation exhaustive de l'architecture, Merise MCD/MLD/MPD, procédures SQL, API, sécurité, tests et contributions individuelles.
- **Journal des Sprints & Choix de Conception** : [`SPRINTS.md`](./SPRINTS.md) — Historique complet des sprints 0 à 8, guide de soutenance et FAQ jury.
- **Guide Conceptuel** : [`Comprendre_le_MCD_banque.pdf`](./docs/Comprendre_le_MCD_banque.pdf) — Guide pédagogique pas-à-pas expliquant chaque bloc du modèle et les règles de gestion associées.
- **Modèle Conceptuel de Données (MCD)** : [`MCD.svg`](./docs/MCD.svg) — Schéma vectoriel Merise généré via Mocodo.
- **Modèle Logique de Données (MLD)** : [`MLD.png`](./docs/MLD.png) — Schéma relationnel complet conçu avec dbdiagram.io.
- **Scripts SQL (Dossier `sql/`)** :
  - [`01_schema_sidpef.sql`](./sql/01_schema_sidpef.sql) — Création des 13 tables, clés primaires/étrangères (`ON DELETE RESTRICT`), contraintes `CHECK` et index.
  - [`02_triggers_metier.sql`](./sql/02_triggers_metier.sql) — Procédure stockée `SP_VALIDER_TRANSACTION` (partie double, mise à jour atomique des soldes) et triggers d'immuabilité sur `MOUVEMENT`.
  - [`03_donnees_test.sql`](./sql/03_donnees_test.sql) — Jeu de données complet (3 agences, 5 clients, 5 comptes, 1 GAB/ATM, 1 bénéficiaire externe, cartes) et test de virement.
  - [`04_requetes_analytiques.sql`](./sql/04_requetes_analytiques.sql) — 5 requêtes métier complexes (fenêtrage `SUM() OVER`, jointures 360°, agrégations, sous-requêtes).
  - [`04b_explain_performance.sql`](./sql/04b_explain_performance.sql) — Démonstrations et benchmarks `EXPLAIN` avant/après indexation avec profilage SQL.
  - [`05_patch_auth.sql`](./sql/05_patch_auth.sql) — Migration DDL/DML d'authentification bcrypt et rôles RBAC.
- **Intégration Python & ORM** :
  - [`config.py`](./config.py) & [`.env.example`](./.env.example) : Isolation des identifiants et configuration paramétrée.
  - [`database.py`](./database.py) : Gestionnaire de pool de connexions MySQL (`mysql.connector.pooling`) et context managers.
  - [`models.py`](./models.py) : Modèles de données typés (`dataclasses`) et hiérarchie d'exceptions bancaires.
  - [`banking_dao.py`](./banking_dao.py) : Couche d'accès aux données (ORM/DAO), exécution atomique de virements via `SP_VALIDER_TRANSACTION` et extraction analytique.
- **API FastAPI & Services REST** :
  - [`api.py`](./api.py) : API RESTful FastAPI sécurisée par JWT, RBAC et intégrité MySQL 8+.
- **Suites de Tests Automatisés (Dossier `tests/`)** :
  - [`test_backend_complet.py`](./tests/test_backend_complet.py) : Suite pytest impitoyable (13 tests) : Auth JWT, ACID/Rollback, Triggers 1644 et équilibre à somme nulle.
  - [`test_frontend.spec.js`](./tests/test_frontend.spec.js) : Suite de tests JSDOM (5 tests) : Persistance JWT, bannières DOM sans rechargement, relevé dynamique.
  - [`test_api.py`](./tests/test_api.py) : Suite de régression API complète (18 tests).
  - [`test_e2e_banking.py`](./tests/test_e2e_banking.py) : Suite de validation end-to-end Python/DAO (7 scénarios réels).

---

## 🏃 Roadmap des Sprints

- [x] **Sprint 1 : Conception Conceptuelle (MCD)**
  - Définition des entités métiers et des règles de gestion bancaires.
  - Élaboration du MCD vectoriel et rédaction du guide de soutenance.
- [x] **Sprint 2 : Modélisation Logique Relationnelle (MLD)**
  - Traduction Merise vers le modèle relationnel.
  - Spécification des types SQL, contraintes d'intégrité référentielle (PK / FK) et héritage par table par classe.
- [x] **Sprint 3 : Implémentation Physique & Logique Métier (MySQL 8+)**
  - Script DDL complet (`sql/01_schema_sidpef.sql`) avec clauses `ON DELETE RESTRICT` et index de performance.
  - Procédure stockée `SP_VALIDER_TRANSACTION` avec vérification de la partie double ($\sum D = \sum C$) et mise à jour atomique.
  - Triggers d'immuabilité comptable (`BEFORE UPDATE` / `BEFORE DELETE` sur `MOUVEMENT`).
  - Jeu d'essai réaliste et validation transactionnelle d'un virement de 2 500 MAD (`sql/03_donnees_test.sql`).
- [x] **Sprint 4 : Requêtage Avancé & Analyse de Performance EXPLAIN (Exigences 8 & 9)**
  - Sélection & filtrage des opérations en anomalie (en attente / rejetées).
  - Vue 360° du client consolidant comptes, cartes et historique de mouvements.
  - Agrégation de liquidité (dépôts/retraits d'espèces par agence).
  - Sous-requête patrimoniale des clients dont le solde cumulé dépasse la moyenne bancaire.
  - Relevé de compte chronologique avec fonction de fenêtrage avancée (`SUM() OVER(PARTITION BY... ORDER BY...)`).
  - Preuve formelle d'optimisation `EXPLAIN` (passage de `type: ALL` à `type: ref` après indexation).
- [x] **Sprint 5 : Intégration Applicative Python & Tests End-to-End (Exigence 10)**
  - Module d'accès aux données (`BankingDAO`) et pool de connexions sécurisé (`DatabaseManager`).
  - Exécution transactionnelle de virements appelant la procédure stockée `SP_VALIDER_TRANSACTION`.
  - Gestion stricte de l'atomicité (`COMMIT`, `ROLLBACK` automatique et levée d'exceptions typées).
  - Validation complète de bout en bout (`python tests/test_e2e_banking.py`) couvrant 7 scénarios réels.
- [x] **Sprint 6 : API RESTful FastAPI & Services Métier (Headless Backend)**
  - Architecture RESTful haute performance (`api.py`) avec validation des schémas Pydantic V2.
  - Endpoints opérationnels : consultation 360°, virement atomique avec appel de `SP_VALIDER_TRANSACTION`, et console d'audit des rejets/triggers.
- [x] **Sprint 7 : Système d'Authentification JWT, RBAC & Login Bancaire**
  - Hachage bcrypt, jetons signés `HS256`, verrouillage cross-client `403 Forbidden`.
  - Intranet bancaire corporate avec typographie *Plus Jakarta Sans*, Nombre d'Or et cloisonnement étanche.
- [x] **Sprint 8 : Validation Qualité Impitoyable & Tests Automatisés E2E**
  - Suite pytest `tests/test_backend_complet.py` (13 tests) : ACID, Rollback, Triggers 1644, Équilibre net 0.00.
  - Suite frontend JSDOM `tests/test_frontend.spec.js` (5 tests) : Sessions JWT, bannières DOM et rendu chronologique.
  - Réorganisation professionnelle de l'arborescence (`sql/`, `docs/`, `tests/`).

---

## 💻 Démarrage Rapide

```bash
# 1. Cloner et installer les dépendances
pip install -r requirements.txt

# 2. Initialiser la base de données MySQL
# Sous Windows : .\setup_db.bat  |  Sous macOS/Linux : ./setup_db.sh

# 3. Démarrer le serveur API & Intranet
python -m uvicorn api:app --reload

# 4. Consulter l'application et la documentation interactive :
# -> Application Intranet : http://127.0.0.1:8000/
# -> Documentation Swagger : http://127.0.0.1:8000/docs

# 5. Exécuter l'ensemble des tests automatisés :
pytest tests/test_backend_complet.py -v
npm test
```
