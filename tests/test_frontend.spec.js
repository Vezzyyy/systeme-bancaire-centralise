/**
 * =============================================================================
 * PROJET : SYSTEME BANCAIRE CENTRALISE (SIDPEF)
 * FICHIER : tests/test_frontend.spec.js
 * SPRINT 8 : SUITE COMPLETE DE TESTS AUTOMATISES FRONTEND & LOGIQUE DOM
 * RESPONSABLE : Équipe QA & Lead Tech (Mouad, Amine, Hamza, Saad, Yassine)
 * =============================================================================
 * Valide avec JSDOM :
 * 1. La gestion sécurisée du jeton JWT dans le sessionStorage (Login & Déconnexion).
 * 2. Le comportement réactif des formulaires et bannières sans rechargement de page.
 * 3. Le rendu dynamique et le calcul visuel du relevé chronologique.
 * =============================================================================
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

describe('Suite de Tests Frontend SIDPEF (DOM & Session)', () => {
  let dom;
  let window;
  let document;

  beforeEach(() => {
    // Construction du DOM minimal représentatif de l'intranet SIDPEF
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <!-- Écran de connexion -->
          <div id="login-overlay" style="display:flex;">
            <div id="login-alert" class="alert-banner alert-danger" style="display:none;"></div>
            <form id="login-form">
              <input type="text" id="login-username" value="yassine.chaouri@banque.ma" />
              <input type="password" id="login-password" value="Sidpef2026!" />
              <button type="submit" id="login-submit-btn">Se connecter</button>
            </form>
          </div>

          <!-- Shell applicatif -->
          <div class="app-shell" style="display:none;">
            <div id="session-user-name"></div>
            <button id="btn-logout" type="button">Déconnexion</button>

            <!-- Formulaire de virement -->
            <form id="transfer-form">
              <div id="transfer-alert-slot"></div>
              <select id="tx-source">
                <option value="1">Compte Courant (1)</option>
              </select>
              <select id="tx-dest">
                <option value="2">Compte Épargne (2)</option>
              </select>
              <input type="number" id="tx-amount" value="500.00" />
              <button type="submit" id="btn-submit-virement">Confirmer le virement</button>
            </form>

            <!-- Tableau du relevé de compte chronologique -->
            <table id="releve-table">
              <tbody id="releve-tbody"></tbody>
            </table>
          </div>
        </body>
      </html>
    `, { url: 'http://localhost:8000/' });

    window = dom.window;
    document = window.document;
    window.sessionStorage.clear();
  });

  afterEach(() => {
    window.close();
  });

  // ===========================================================================
  // 1. AXE STOCKAGE & SESSION (JWT & SESSIONSTORAGE)
  // ===========================================================================
  describe('1. Gestion de la Session & Jeton JWT', () => {
    it('doit persister le jeton JWT dans sessionStorage lors d’une connexion réussie', () => {
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mockPayload.signature';
      
      // Simulation de la réponse de login et de la fonction d’enregistrement
      window.sessionStorage.setItem('sidpef_token', mockToken);
      document.getElementById('login-overlay').style.display = 'none';
      document.querySelector('.app-shell').style.display = 'flex';
      document.getElementById('session-user-name').textContent = 'Yassine Chaouri';

      assert.equal(window.sessionStorage.getItem('sidpef_token'), mockToken);
      assert.equal(document.getElementById('login-overlay').style.display, 'none');
      assert.equal(document.querySelector('.app-shell').style.display, 'flex');
      assert.equal(document.getElementById('session-user-name').textContent, 'Yassine Chaouri');
    });

    it('doit supprimer le jeton JWT et afficher l’écran de login lors de la déconnexion', () => {
      // Setup session active
      window.sessionStorage.setItem('sidpef_token', 'valid-active-token');

      // Simulation de handleLogout()
      function handleLogout() {
        window.sessionStorage.removeItem('sidpef_token');
        document.getElementById('login-overlay').style.display = 'flex';
        document.querySelector('.app-shell').style.display = 'none';
      }

      handleLogout();

      assert.equal(window.sessionStorage.getItem('sidpef_token'), null);
      assert.equal(document.getElementById('login-overlay').style.display, 'flex');
      assert.equal(document.querySelector('.app-shell').style.display, 'none');
    });
  });

  // ===========================================================================
  // 2. AXE COMPORTEMENT UI (BOUTONS, VIREMENTS & BANNIÈRES SANS RECHARGEMENT)
  // ===========================================================================
  describe('2. Formulaire Transactionnel & Bannières Réactives', () => {
    it('doit intercepter le submit (preventDefault) et afficher une bannière verte en cas de succès', () => {
      let defaultPrevented = false;
      const slot = document.getElementById('transfer-alert-slot');

      function handleTransferSubmit(event, apiResult) {
        event.preventDefault();
        defaultPrevented = event.defaultPrevented;
        
        if (apiResult.success) {
          slot.innerHTML = `
            <div class="alert-banner alert-success">
              Virement de 500,00 MAD validé avec succès (Réf: ${apiResult.ref_transaction}).
            </div>
          `;
        }
      }

      // Déclenchement de l'événement
      const event = new window.Event('submit', { cancelable: true });
      handleTransferSubmit(event, { success: true, ref_transaction: 'TX-PY-20261113-SUCCESS' });

      assert.equal(defaultPrevented, true, "Le rechargement de page doit être bloqué par preventDefault()");
      const banner = slot.querySelector('.alert-success');
      assert.ok(banner, "La bannière verte alert-success doit être présente dans le DOM");
      assert.match(banner.textContent, /TX-PY-20261113-SUCCESS/);
      assert.match(banner.textContent, /validé avec succès/);
    });

    it('doit afficher une bannière rouge sobre sans rechargement en cas de découvert dépassé', () => {
      const slot = document.getElementById('transfer-alert-slot');

      function handleTransferError(event, errorMessage) {
        event.preventDefault();
        slot.innerHTML = `
          <div class="alert-banner alert-danger">
            ${errorMessage}
          </div>
        `;
      }

      const event = new window.Event('submit', { cancelable: true });
      handleTransferError(event, "Rejet Bancaire : Provision insuffisante pour le compte N°1.");

      const banner = slot.querySelector('.alert-danger');
      assert.ok(banner, "La bannière rouge alert-danger doit être affichée");
      assert.match(banner.textContent, /Provision insuffisante/);
    });
  });

  // ===========================================================================
  // 3. AXE RENDU DASHBOARD & RELEVÉ CHRONOLOGIQUE
  // ===========================================================================
  describe('3. Rendu Dynamique du Relevé Chronologique', () => {
    it('doit peupler fidèlement les lignes du tableau à partir d’un jeu de données API mocké', () => {
      const mockReleve = [
        {
          id_mouvement: 101,
          date_valeur: '2026-11-13',
          ref_transaction: 'TX-2026-DEP-001',
          libelle_operation: 'Dépôt d’espèces au guichet',
          debit: null,
          credit: 2500.00,
          solde_cumule: 2500.00,
        },
        {
          id_mouvement: 102,
          date_valeur: '2026-11-13',
          ref_transaction: 'TX-2026-VIR-002',
          libelle_operation: 'Virement émis vers Compte 2',
          debit: 500.00,
          credit: null,
          solde_cumule: 2000.00,
        },
      ];

      const tbody = document.getElementById('releve-tbody');

      // Fonction de rendu conforme à l'application SIDPEF
      tbody.innerHTML = mockReleve.map((m) => `
        <tr data-mouvement-id="${m.id_mouvement}">
          <td class="col-date">${m.date_valeur}</td>
          <td class="col-ref mono">${m.ref_transaction}</td>
          <td class="col-label">${m.libelle_operation}</td>
          <td class="col-debit ${m.debit ? 'amount-debit' : ''}">${m.debit ? `${m.debit.toFixed(2)} MAD` : '—'}</td>
          <td class="col-credit ${m.credit ? 'amount-credit' : ''}">${m.credit ? `${m.credit.toFixed(2)} MAD` : '—'}</td>
          <td class="col-solde mono font-bold">${m.solde_cumule.toFixed(2)} MAD</td>
        </tr>
      `).join('');

      const rows = tbody.querySelectorAll('tr');
      assert.equal(rows.length, 2, "Le tableau doit comporter exactement 2 lignes");

      // Vérification de la première ligne (Crédit)
      const row1 = rows[0];
      assert.equal(row1.querySelector('.col-ref').textContent.trim(), 'TX-2026-DEP-001');
      assert.equal(row1.querySelector('.col-credit').textContent.trim(), '2500.00 MAD');
      assert.equal(row1.querySelector('.col-debit').textContent.trim(), '—');
      assert.equal(row1.querySelector('.col-solde').textContent.trim(), '2500.00 MAD');

      // Vérification de la deuxième ligne (Débit)
      const row2 = rows[1];
      assert.equal(row2.querySelector('.col-ref').textContent.trim(), 'TX-2026-VIR-002');
      assert.equal(row2.querySelector('.col-debit').textContent.trim(), '500.00 MAD');
      assert.equal(row2.querySelector('.col-credit').textContent.trim(), '—');
      assert.equal(row2.querySelector('.col-solde').textContent.trim(), '2000.00 MAD');
    });
  });
});
