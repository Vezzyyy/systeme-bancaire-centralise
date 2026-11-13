#!/usr/bin/env bash
# ========================================================
# INITIALISATION DE LA BASE BANCAIRE SIDPEF (MySQL 8+)
# ========================================================
set -e

echo "========================================================"
echo " INITIALISATION DE LA BASE BANCAIRE SIDPEF (MySQL 8+)"
echo "========================================================"
echo ""

read -p "Nom d'utilisateur MySQL [defaut: root]: " DB_USER
DB_USER=${DB_USER:-root}

read -sp "Mot de passe MySQL pour $DB_USER: " DB_PASS
echo ""
echo ""

echo "[1/4] Execution de 01_schema_sidpef.sql..."
mysql -u "$DB_USER" -p"$DB_PASS" < sql/01_schema_sidpef.sql

echo "[2/4] Execution de 02_triggers_metier.sql..."
mysql -u "$DB_USER" -p"$DB_PASS" < sql/02_triggers_metier.sql

echo "[3/4] Execution de 03_donnees_test.sql..."
mysql -u "$DB_USER" -p"$DB_PASS" < sql/03_donnees_test.sql

echo "[4/4] Execution de 05_patch_auth.sql..."
mysql -u "$DB_USER" -p"$DB_PASS" < sql/05_patch_auth.sql

echo ""
echo "========================================================"
echo " SUCCES : La base banque_centrale_db est prete a l'emploi !"
echo "========================================================"
