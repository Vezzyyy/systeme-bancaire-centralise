# 🚀 Guide d'Installation & Prise en Main — Système Bancaire SIDPEF
### *Tutoriel pour les membres de l'équipe (Yassine, Saad, Hamza, Mouad, Amine)*

Ce guide pas-à-pas explique comment cloner le projet depuis GitHub, initialiser la base de données MySQL 8+, démarrer le serveur FastAPI et tester toutes les fonctionnalités bancaires en 5 minutes.

---

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir installé sur votre machine :
1. **Git** ([git-scm.com](https://git-scm.com/))
2. **Python 3.10+** ([python.org](https://www.python.org/)) avec `pip`
3. **MySQL Server 8.0+** (démarré et accessible en local sur le port 3306)
4. *(Optionnel)* **Node.js 18+** (uniquement si vous souhaitez exécuter les tests frontend JSDOM)

---

## ⚙️ Étape 1 : Cloner le Répertoire GitHub

Ouvrez un terminal (PowerShell, CMD ou Bash) et lancez :

```bash
git clone https://github.com/Vezzyyy/systeme-bancaire-centralise.git
cd systeme-bancaire-centralise
```

---

## 🐍 Étape 2 : Créer l'Environnement Virtuel Python & Installer les Dépendances

Il est recommandé d'utiliser un environnement virtuel isolé :

### Sous Windows (PowerShell / CMD) :
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Sous macOS / Linux :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔐 Étape 3 : Configurer les Identifiants MySQL (`.env`)

Copiez le fichier d'exemple `.env.example` en `.env` :

* **Windows (PowerShell)** : `Copy-Item .env.example .env`
* **Windows (CMD)** : `copy .env.example .env`
* **macOS / Linux** : `cp .env.example .env`

Ouvrez le fichier `.env` et adaptez votre mot de passe MySQL si nécessaire :

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=votre_mot_de_passe_mysql
DB_NAME=banque_centrale_db
```

*(Si votre mot de passe root MySQL est `root`, la configuration par défaut fonctionne immédiatement sans modification).*

---

## 🗄️ Étape 4 : Charger la Base de Données dans MySQL

Nous avons préparé **trois méthodes** simples au choix :

### Option A : Via le Script Automatique (Recommandé)

* **Windows** : Double-cliquez sur `setup_db.bat` (ou tapez `.\setup_db.bat` dans votre terminal).
* **macOS / Linux** : Tapez `chmod +x setup_db.sh && ./setup_db.sh`.

Le script vous demande votre mot de passe MySQL et charge automatiquement les 4 scripts dans le bon ordre.

---

### Option B : Via la Ligne de Commande (CLI)

Exécutez dans votre terminal à la racine du projet :

```bash
# 1. Création de la base banque_centrale_db, des 13 tables et des index
mysql -u root -p < sql/01_schema_sidpef.sql

# 2. Création de la procédure SP_VALIDER_TRANSACTION et des triggers 1644
mysql -u root -p < sql/02_triggers_metier.sql

# 3. Injection du jeu de données de test (Agences, Clients, Comptes, Caisses)
mysql -u root -p < sql/03_donnees_test.sql

# 4. Patch d'authentification (Mots de passe hachés bcrypt et rôles RBAC)
mysql -u root -p < sql/05_patch_auth.sql
```

---

### Option C : Via MySQL Workbench (Interface Graphique)

1. Ouvrez **MySQL Workbench** et connectez-vous à votre instance locale.
2. Allez dans le menu : **File $\rightarrow$ Open SQL Script...**
3. Ouvrez et exécutez (icône éclair ⚡) successivement les 4 fichiers du dossier `sql/` dans cet ordre :
   - `01_schema_sidpef.sql`
   - `02_triggers_metier.sql`
   - `03_donnees_test.sql`
   - `05_patch_auth.sql`
4. Faites un clic droit sur le panneau des schémas à gauche et cliquez sur **Refresh All** : la base `banque_centrale_db` avec ses 13 tables apparaît !

---

## 🌐 Étape 5 : Démarrer le Serveur Applicatif

Assurez-vous que votre environnement virtuel est actif (`(venv)`), puis lancez :

```bash
python -m uvicorn api:app --reload
```

Le serveur démarre immédiatement :
* **Application Intranet Bancaire (SPA)** : Ouvrez votre navigateur sur **`http://127.0.0.1:8000/`**
* **Documentation Interactive OpenAPI (Swagger)** : Ouvrez **`http://127.0.0.1:8000/docs`**
* **Vérification de Santé API** : Ouvrez **`http://127.0.0.1:8000/api/health`** (doit renvoyer `{"status": "UP"}`)

---

## 🔑 Étape 6 : Identifiants de Test Préconfigurés

### 1. Comptes Clients (Espace Retail)
Tous les comptes clients partagent le mot de passe : **`Sidpef2026!`**

| Client | Email | Identifiant Alternatif (CIN) | Solde Initial |
| :--- | :--- | :--- | :--- |
| **Yassine Chaouri** | `yassine.chaouri@banque.ma` | `BE123456` | ~ 12 500,00 MAD |
| **Saad Joudali** | `saad.joudali@banque.ma` | `BK654321` | ~ 8 200,00 MAD |
| **Hamza Sibous** | `hamza.sibous@banque.ma` | `CD789012` | ~ 45 000,00 MAD |
| **Mouad Talibi** | `mouad.talibi@banque.ma` | `EE345678` | ~ 3 100,00 MAD |
| **Amine Aouzagh** | `amine.aouzagh@banque.ma` | `AA901234` | ~ 19 800,00 MAD |

### 2. Compte Administrateur (Console Back-Office)
* **Email** : `admin@sidpef.ma` *(ou `ADMIN001`)*
* **Mot de passe** : **`AdminSidpef2026!`**

---

## 🧪 Étape 7 : Parcours de Test Recommandé

### Scénario A : Test de l'Espace Client
1. Connectez-vous avec `yassine.chaouri@banque.ma` / `Sidpef2026!`.
2. Constatez la **position globale consolidée** et le tableau du **relevé chronologique** avec le solde progressif calculé en temps réel via `SUM() OVER`.
3. **Tester un virement réussi** :
   - Choisissez le compte destinataire de Saad Joudali.
   - Montant : `500.00` MAD.
   - Motif : `Remboursement test`.
   - Cliquez sur **Valider le virement** $\rightarrow$ Bannière verte instantanée, les soldes et le relevé se mettent à jour sans recharger la page.
4. **Tester le rejet pour solde insuffisant (ACID Rollback)** :
   - Tentez un virement de `999999.00` MAD.
   - Cliquez sur **Valider le virement** $\rightarrow$ Bannière rouge indiquant la provision insuffisante. Aucun centime n'a été débité (Rollback strict).
5. **Tester le Kill Switch de la carte bancaire** :
   - Dans la section Cartes, cliquez sur le bouton pour bloquer la carte $\rightarrow$ Le statut passe à `BLOQUEE`.

---

### Scénario B : Test de la Console Back-Office Admin
1. Déconnectez-vous, puis connectez-vous avec `admin@sidpef.ma` / `AdminSidpef2026!`.
2. Cliquez sur **"Voir toutes les anomalies $\rightarrow$"** dans la barre latérale ou la tuile d'anomalies $\rightarrow$ La liste des transactions rejetées/suspectes s'affiche en temps réel.
3. Allez dans le module **Audit & Piste d'Audit** :
   - Cliquez sur **"Vérifier l'Équilibre Global"** $\rightarrow$ Le système calcule $\sum \text{Mouvements}$ et confirme un solde net rigoureusement égal à `0.00 MAD` (Partie double respectée).
   - Cliquez sur **"Tester l'interception du Trigger"** $\rightarrow$ Le système tente un `UPDATE` direct sur un mouvement et affiche l'erreur MySQL interceptée : `Code 1644 / SQLSTATE 45000 (REGLE RG2 : Violation d'immuabilite comptable)`.

---

## 🏆 Étape 8 : Lancer les Tests Automatisés

Dans un second terminal avec l'environnement virtuel actif :

```bash
# 1. Exécuter la suite backend impitoyable (13 tests Pytest)
pytest tests/test_backend_complet.py -v

# 2. Exécuter l'intégralité des tests de régression API (18 tests)
pytest tests/test_api.py -v

# 3. Exécuter les scénarios réels Python DAO (7 tests E2E)
python tests/test_e2e_banking.py

# 4. (Si Node.js installé) Exécuter les tests frontend JSDOM (5 tests)
npm test
```

Résultat attendu : **100% des tests doivent passer avec succès (PASSED)**.

---
*En cas de question ou de problème de connexion MySQL, vérifiez que le service MySQL tourne bien dans vos services Windows/macOS.*
