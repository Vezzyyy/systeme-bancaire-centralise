@echo off
chcp 65001 > nul
echo ========================================================
echo  INITIALISATION DE LA BASE BANCAIRE SIDPEF (MySQL 8+)
echo ========================================================
echo.
set /p DB_USER="Nom d'utilisateur MySQL [defaut: root]: "
if "%DB_USER%"=="" set DB_USER=root

set /p DB_PASS="Mot de passe MySQL pour %DB_USER%: "
echo.
echo [1/4] Execution de 01_schema_sidpef.sql (Creation BD et tables)...
mysql -u %DB_USER% -p%DB_PASS% < sql\01_schema_sidpef.sql
if %ERRORLEVEL% NEQ 0 goto error

echo [2/4] Execution de 02_triggers_metier.sql (Procedure ACID et Triggers 1644)...
mysql -u %DB_USER% -p%DB_PASS% < sql\02_triggers_metier.sql
if %ERRORLEVEL% NEQ 0 goto error

echo [3/4] Execution de 03_donnees_test.sql (Jeu d'essai et agences)...
mysql -u %DB_USER% -p%DB_PASS% < sql\03_donnees_test.sql
if %ERRORLEVEL% NEQ 0 goto error

echo [4/4] Execution de 05_patch_auth.sql (Comptes bcrypt et roles RBAC)...
mysql -u %DB_USER% -p%DB_PASS% < sql\05_patch_auth.sql
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo ========================================================
echo  SUCCES : La base banque_centrale_db est prete a l'emploi !
echo ========================================================
pause
exit /b 0

:error
echo.
echo [ERREUR] L'initialisation a echoue. Verifiez vos identifiants MySQL.
pause
exit /b 1
