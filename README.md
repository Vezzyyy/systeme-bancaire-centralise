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

## 🗂️ Documents du Projet

- **Guide Conceptuel** : [`Comprendre_le_MCD_banque.pdf`](./Comprendre_le_MCD_banque.pdf) — Guide pédagogique pas-à-pas expliquant chaque bloc du modèle et les règles de gestion associées.
- **Modèle Conceptuel de Données (MCD)** : [`MCD.svg`](./MCD.svg) — Schéma vectoriel Merise généré via Mocodo.
- **Modèle Logique de Données (MLD)** : [`MLD.png`](./MLD.png) — Schéma relationnel complet (tables, types de données, clés primaires et étrangères, contraintes de non-nullité) conçu avec dbdiagram.io.

---

## 🏃 Roadmap des Sprints

- [x] **Sprint 1 : Conception Conceptuelle (MCD)**
  - Définition des entités métiers et des règles de gestion bancaires.
  - Élaboration du MCD vectoriel et rédaction du guide de soutenance.
- [x] **Sprint 2 : Modélisation Logique Relationnelle (MLD)**
  - Traduction Merise vers le modèle relationnel.
  - Spécification des types SQL, contraintes d'intégrité référentielle (PK / FK) et héritage par table par classe.
- [ ] **Sprint 3 : Implémentation Physique (MPD & Scripts DDL)**
  - Scripts SQL de création des tables, index et contraintes de vérification (`CHECK`).
  - Déclencheurs (triggers) ou procédures pour garantir l'équilibre débit/crédit et la cohérence des soldes.
- [ ] **Sprint 4 : Jeu d'essai & Scénarios Bancaires (Data Seeding)**
  - Données de test réalistes simulant des flux complets (ouvertures, retraits guichet, paiements par carte, virements interbancaires).
- [ ] **Sprint 5 : Requêtes d'Exploitation & Reporting**
  - Relevés de comptes, calculs d'encours, détection d'anomalies et suivi des soldes en temps réel.
