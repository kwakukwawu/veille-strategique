/**
 * Application Veille Stratégique - Script principal
 * Gère les appels API et interactions utilisateur
 */

const API_BASE = '/api';

class VeilleStrategique {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.profile = null;
        this.scrapeAllRunning = false;
        this.toastContainer = null;
        this.loadingOverlay = null;
        this.loadingCount = 0;
        this.revealObserver = null;
        this.ensureUi();
        this.initScrollReveal();
        this.initEventListeners();
        this.initAuthUi();
    }

    initScrollReveal() {
        if (this.revealObserver) return;
        if (!('IntersectionObserver' in window)) return;

        this.revealObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('reveal-visible');
                        this.revealObserver.unobserve(entry.target);
                    }
                });
            },
            {
                root: null,
                rootMargin: '0px 0px -5% 0px',
                threshold: 0.08
            }
        );
    }

    revealElements(rootEl = document) {
        if (!this.revealObserver) return;
        const els = rootEl.querySelectorAll('.reveal:not(.reveal-visible)');
        els.forEach((el) => this.revealObserver.observe(el));
    }

    debounce(fn, waitMs = 300) {
        let t;
        return (...args) => {
            if (t) clearTimeout(t);
            t = setTimeout(() => fn(...args), waitMs);
        };
    }

    ensureUi() {
        if (!this.toastContainer) {
            let el = document.querySelector('.toast-container');
            if (!el) {
                el = document.createElement('div');
                el.className = 'toast-container';
                document.body.appendChild(el);
            }
            this.toastContainer = el;
        }

        if (!this.loadingOverlay) {
            let overlay = document.querySelector('.loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'loading-overlay';
                overlay.innerHTML = `
                    <div class="loading-card">
                        <div class="loading-row">
                            <div class="spinner"></div>
                            <div>
                                <div style="font-weight:700;">Chargement...</div>
                                <div style="color: var(--text-light);">Merci de patienter</div>
                            </div>
                        </div>
                    </div>
                `;
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) this.hideLoading();
                });
                document.body.appendChild(overlay);
            }
            this.loadingOverlay = overlay;
        }
    }

    async authRequest(endpoint, options = {}) {
        const url = `${API_BASE.replace('/api', '')}/auth${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
        const makeHeaders = (includeBearer) => {
            const h = {
                'Content-Type': 'application/json',
                ...options.headers
            };
            if (includeBearer && this.token) {
                h['Authorization'] = `Bearer ${this.token}`;
            }
            return h;
        };

        const doFetch = async (includeBearer) => {
            const response = await fetch(url, {
                ...options,
                headers: makeHeaders(includeBearer)
            });
            const data = await response.json().catch(() => ({}));
            return { response, data };
        };

        // 1) Tentative avec Bearer si présent
        let { response, data } = await doFetch(true);

        // 2) Si Bearer invalide, on purge le token et on retente sans Authorization.
        // Cela permet au navigateur d'utiliser le Basic Auth (popup) en mode "mot de passe unique".
        if (!response.ok && response.status === 401 && this.token) {
            const msg = (data && (data.erreur || data.message)) ? (data.erreur || data.message) : '';
            const looksLikeTokenProblem = /token/i.test(msg) || /non authent/i.test(msg);
            if (looksLikeTokenProblem) {
                localStorage.removeItem('auth_token');
                this.token = null;
                ({ response, data } = await doFetch(false));
            }
        }

        if (!response.ok) {
            const msg = (data && (data.erreur || data.message)) ? (data.erreur || data.message) : `Erreur ${response.status}`;
            throw new Error(msg);
        }
        return data;
    }

    async initAuthUi() {
        const nav = document.querySelector('header nav');
        if (!nav) return;

        const loginLink = Array.from(nav.querySelectorAll('a')).find(a => (a.getAttribute('href') || '') === '/connexion');
        if (!loginLink) return;

        try {
            // En mode Basic Auth (mot de passe unique), il n'y a pas de token.
            // On tente quand même /auth/profil: si Basic Auth est valide, l'API répond 200.
            const profil = await this.authRequest('/profil', { method: 'GET' });
            this.profile = profil;

            if (this.token) {
                loginLink.textContent = 'Déconnexion';
                loginLink.setAttribute('href', '#');
                loginLink.onclick = (e) => {
                    e.preventDefault();
                    this.handleLogout();
                };
            } else {
                // Basic Auth: pas de déconnexion classique. On propose de forcer une ré-auth.
                loginLink.textContent = 'Changer utilisateur';
                loginLink.setAttribute('href', '/auth/reauth');
                loginLink.onclick = null;
            }

            if (profil && profil.role === 'admin') {
                const already = Array.from(nav.querySelectorAll('a')).find(a => (a.getAttribute('href') || '') === '/admin/compte');
                if (!already) {
                    const a = document.createElement('a');
                    a.setAttribute('href', '/admin/compte');
                    a.textContent = 'Compte';
                    nav.insertBefore(a, loginLink);
                }
            }
        } catch (e) {
            // Ni token ni Basic Auth valide
            if (this.token) {
                this.handleLogout();
            }
            loginLink.textContent = 'Connexion';
            loginLink.setAttribute('href', '/connexion');
            loginLink.onclick = null;
        }
    }

    showLoading(message) {
        this.ensureUi();
        this.loadingCount += 1;
        const title = this.loadingOverlay.querySelector('.loading-card div[style*="font-weight"]');
        if (title && message) title.textContent = message;
        this.loadingOverlay.classList.add('active');
    }

    hideLoading() {
        if (!this.loadingOverlay) return;
        this.loadingCount = Math.max(0, this.loadingCount - 1);
        if (this.loadingCount === 0) {
            this.loadingOverlay.classList.remove('active');
        }
    }

    async withLoading(message, fn) {
        this.showLoading(message);
        try {
            return await fn();
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Initialiser les écouteurs d'événements
     */
    initEventListeners() {
        // Bouton de connexion
        const btnLogin = document.getElementById('btn-login');
        if (btnLogin) {
            btnLogin.addEventListener('click', () => this.handleLogin());
        }

        // Bouton de déconnexion
        const btnLogout = document.getElementById('btn-logout');
        if (btnLogout) {
            btnLogout.addEventListener('click', () => this.handleLogout());
        }
    }

    /**
     * Effectuer une requête API
     */
    async apiRequest(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        try {
            const makeHeaders = (includeBearer) => {
                const h = {
                    'Content-Type': 'application/json',
                    ...options.headers
                };
                if (includeBearer && this.token) {
                    h['Authorization'] = `Bearer ${this.token}`;
                }
                return h;
            };

            const doFetch = async (includeBearer) => {
                const response = await fetch(url, {
                    ...options,
                    headers: makeHeaders(includeBearer)
                });
                const data = await response.json().catch(() => ({}));
                return { response, data };
            };

            // 1) Tentative avec Bearer si présent
            let { response, data } = await doFetch(true);

            // 2) Si Bearer invalide, purge et retente sans Authorization
            if (!response.ok && response.status === 401 && this.token) {
                const msg = (data && (data.erreur || data.message)) ? (data.erreur || data.message) : '';
                const looksLikeTokenProblem = /token/i.test(msg) || /non authent/i.test(msg) || /session/i.test(msg);
                if (looksLikeTokenProblem) {
                    localStorage.removeItem('auth_token');
                    this.token = null;
                    ({ response, data } = await doFetch(false));
                }
            }

            if (!response.ok) {
                const msg = (data && (data.erreur || data.message)) ? (data.erreur || data.message) : `Erreur ${response.status}`;
                throw new Error(msg);
            }

            return data;
        } catch (error) {
            console.error('Erreur API:', error);
            throw error;
        }
    }

    /**
     * Lister les offres
     */
    async listerOffres(page = 1, filtres = {}) {
        const params = new URLSearchParams({ page, ...filtres });
        return this.apiRequest(`/offres?${params}`);
    }

    /**
     * Obtenir les détails d'une offre
     */
    async obtenirOffre(id) {
        return this.apiRequest(`/offres/${id}`);
    }

    /**
     * Rechercher des offres
     */
    async rechercher(query, page = 1) {
        return this.apiRequest(`/offres/rechercher?q=${encodeURIComponent(query)}&page=${page}`);
    }

    /**
     * Lister les mots-clés
     */
    async listerMotsCles(page = 1) {
        return this.apiRequest(`/mots-cles?page=${page}`);
    }

    /**
     * Ajouter un mot-clé (admin)
     */
    async ajouterMotCle(mot, categorie) {
        return this.apiRequest('/mots-cles', {
            method: 'POST',
            body: JSON.stringify({ mot, categorie })
        });
    }

    /**
     * Lister les sources
     */
    async listerSources() {
        return this.apiRequest('/sources');
    }

    /**
     * Obtenir les statistiques
     */
    async obtenirStats() {
        return this.apiRequest('/stats');
    }

    /**
     * Obtenir le statut du scheduler
     */
    async obtenirStatusScheduler() {
        return this.apiRequest('/scheduler/status');
    }

    async obtenirStatusAI() {
        return this.apiRequest('/ai/status');
    }

    /**
     * Exécuter un scraper
     */
    async executerScraper(scraperKey) {
        return this.withLoading('Scraping en cours...', async () => {
            try {
                const res = await this.apiRequest(`/scheduler/executer/${scraperKey}`, {
                    method: 'POST'
                });
                this.showNotification(res.message || 'Scraping démarré', 'success');
                return res;
            } catch (err) {
                const msg = (err && err.message) ? err.message : '';
                if (msg.includes('Session expirée') || msg.toLowerCase().includes('401') || msg.toLowerCase().includes('permission')) {
                    this.showNotification('Connectez-vous en tant qu\'administrateur pour lancer le scraping', 'warning');
                } else {
                    this.showNotification('Erreur lors de l\'exécution du scraper', 'error');
                }
                throw err;
            }
        });
    }

    /**
     * Exécuter tous les scrapers
     */
    async executerTousScrapers() {
        const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

        if (this.scrapeAllRunning) {
            this.showNotification('Un scraping global est déjà en cours...', 'warning');
            return;
        }

        this.scrapeAllRunning = true;
        return this.withLoading('Scraping global en cours...', async () => {
            try {
                if (!this.token) {
                    this.showNotification('Connectez-vous en tant qu\'administrateur pour lancer le scraping', 'warning');
                    throw new Error('Accès admin requis');
                }

                const start = await this.apiRequest('/scheduler/executer-tous/async', { method: 'POST' });
                let job = start.job || null;

                for (let i = 0; i < 180; i++) { // ~6 minutes
                    const status = await this.apiRequest('/scheduler/executer-tous/status');
                    job = status.job;
                    if (job && job.running === false) break;
                    await sleep(2000);
                }

                if (!job) {
                    this.showNotification('Scraping: statut indisponible', 'warning');
                    return start;
                }

                if (job.error) {
                    this.showNotification('Erreur scraping: ' + job.error, 'error');
                    return { job };
                }

                const results = (job.result && job.result.results) ? job.result.results : [];
                const okCount = results.filter(r => r && r.result && r.result.statut === 'succes').length;
                const errCount = results.filter(r => r && (r.statut === 'erreur' || (r.result && r.result.statut === 'erreur'))).length;
                this.showNotification(`Scraping terminé: ${okCount} succès, ${errCount} erreurs. Certaines sources peuvent bloquer (403/404).`, 'success');
                return { job };
            } catch (err) {
                const msg = (err && err.message) ? err.message : '';
                if (msg.includes('Session expirée') || msg.toLowerCase().includes('401') || msg.toLowerCase().includes('permission')) {
                    this.showNotification('Connectez-vous en tant qu\'administrateur pour lancer le scraping', 'warning');
                } else {
                    this.showNotification('Erreur lors du scraping global', 'error');
                }
                throw err;
            } finally {
                this.scrapeAllRunning = false;
                // Fail-safe: éviter que l'overlay reste bloqué en mode "patienter"
                this.loadingCount = 0;
                if (this.loadingOverlay) this.loadingOverlay.classList.remove('active');
            }
        });
    }

    /**
     * Gestion de la connexion
     */
    async handleLogin() {
        const email = document.getElementById('email')?.value;
        const password = document.getElementById('password')?.value;

        if (!email || !password) {
            this.showNotification('Email et mot de passe requis', 'warning');
            return;
        }

        await this.withLoading('Connexion...', async () => {
            try {
                const response = await fetch(`${API_BASE.replace('/api', '')}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (!response.ok) {
                    this.showNotification('Connexion échouée: ' + (data.erreur || 'Erreur'), 'error');
                    return;
                }

                localStorage.setItem('auth_token', data.token);
                this.token = data.token;
                this.showNotification('Connexion réussie', 'success');
                window.location.href = '/offres';
            } catch (error) {
                this.showNotification('Erreur de connexion: ' + error.message, 'error');
            }
        });
    }

    /**
     * Déconnexion
     */
    handleLogout() {
        localStorage.removeItem('auth_token');
        this.token = null;
        window.location.href = '/connexion';
    }

    /**
     * Afficher une notification
     */
    showNotification(message, type = 'info') {
        this.ensureUi();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div style="flex:1;">
                <div class="toast-title">${type === 'success' ? 'Succès' : type === 'error' ? 'Erreur' : type === 'warning' ? 'Attention' : 'Info'}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Fermer">×</button>
        `;

        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) closeBtn.addEventListener('click', () => toast.remove());

        this.toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast && toast.parentElement) toast.remove();
        }, 4500);
    }

    /**
     * Formater une date
     */
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        if (!date || Number.isNaN(date.getTime())) return '-';
        if (date.getTime() === 0) return '-';
        const hasTime = (date.getHours() !== 0) || (date.getMinutes() !== 0);
        if (!hasTime) {
            return date.toLocaleDateString('fr-FR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
        return date.toLocaleString('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Tronquer un texte
     */
    truncate(text, length = 100) {
        if (!text) return '';
        return text.length > length ? text.substring(0, length) + '...' : text;
    }

    detectLieuExecution(offre) {
        const raw = [offre?.titre, offre?.description].filter(Boolean).join(' ').toLowerCase();
        if (!raw) return 'Côte d\'Ivoire';

        const villes = [
            'abidjan', 'cocody', 'yopougon', 'plateau', 'treichville', 'marcory',
            'yamoussoukro', 'bouaké', 'bouake', 'san pedro', 'san-pedro', 'korhogo',
            'daloa', 'man', 'gagnoa', 'abengourou', 'odienné', 'odienne', 'bondoukou',
            'dimbokro', 'agnoibilékrou', 'agnoibilekrou', 'agboville', 'grand-bassam', 'grand bassam',
            'bouaflé', 'bouafle', 'divo', 'sassandra', 'anyama', 'bingerville', 'assinie'
        ];

        for (const v of villes) {
            if (raw.includes(v)) {
                const pretty = v
                    .split(' ')
                    .map(w => w ? (w[0].toUpperCase() + w.slice(1)) : w)
                    .join(' ');
                return `${pretty}, Côte d'Ivoire`;
            }
        }

        if (raw.includes("côte d'ivoire") || raw.includes('cote d\'ivoire') || raw.includes('cote divoire') || raw.includes('ivory coast') || raw.includes('ci') || raw.includes('civ')) {
            return "Côte d'Ivoire";
        }

        return "Côte d'Ivoire";
    }
}

// Initialiser l'app globalement
const app = new VeilleStrategique();

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.card, section').forEach((el) => {
        el.classList.add('reveal');
    });
    app.revealElements(document);
});
