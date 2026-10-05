(() => {
    const OVERLAY_ID = 'financial-auth-overlay';
    const SIGNOUT_ID = 'financial-auth-signout';

    const style = document.createElement('style');
    style.textContent = `
        #${OVERLAY_ID} {
            position: fixed;
            inset: 0;
            z-index: 2147483000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background:
                radial-gradient(circle at 50% 35%, rgba(102,167,255,.16), transparent 32%),
                rgba(3, 9, 17, .78);
            backdrop-filter: blur(9px) saturate(.88);
            -webkit-backdrop-filter: blur(9px) saturate(.88);
            transition: opacity .28s ease, visibility .28s ease;
        }
        #${OVERLAY_ID}.is-hidden {
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }
        #${OVERLAY_ID} .auth-orbit {
            position: absolute;
            width: 390px;
            height: 390px;
            border: 1px solid rgba(102,167,255,.16);
            border-radius: 50%;
            box-shadow: 0 0 90px rgba(102,167,255,.08);
            animation: auth-orbit 12s linear infinite;
        }
        #${OVERLAY_ID} .auth-orbit::before,
        #${OVERLAY_ID} .auth-orbit::after {
            content: '';
            position: absolute;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #66a7ff;
            box-shadow: 0 0 18px rgba(102,167,255,.9);
        }
        #${OVERLAY_ID} .auth-orbit::before { top: 18px; left: 50%; }
        #${OVERLAY_ID} .auth-orbit::after { bottom: 58px; right: 22px; opacity: .55; }
        @keyframes auth-orbit { to { transform: rotate(360deg); } }
        #${OVERLAY_ID} .auth-card {
            position: relative;
            width: min(430px, 100%);
            padding: 34px;
            border-radius: 24px;
            border: 1px solid rgba(148,163,184,.22);
            background: linear-gradient(145deg, rgba(15,29,45,.96), rgba(8,18,29,.94));
            box-shadow: 0 32px 90px rgba(0,0,0,.48), inset 0 1px 0 rgba(255,255,255,.07);
            color: #f8fbff;
            overflow: hidden;
        }
        #${OVERLAY_ID} .auth-card::before {
            content: '';
            position: absolute;
            inset: 0;
            pointer-events: none;
            background: linear-gradient(135deg, rgba(102,167,255,.10), transparent 35%, rgba(50,210,150,.05));
        }
        #${OVERLAY_ID} .auth-brand {
            position: relative;
            margin-bottom: 26px;
        }
        #${OVERLAY_ID} .auth-kicker {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .18em;
            text-transform: uppercase;
            color: #7fb7ff;
            margin-bottom: 8px;
        }
        #${OVERLAY_ID} .auth-title {
            margin: 0;
            font-size: 30px;
            line-height: 1.05;
            font-weight: 850;
            letter-spacing: -.035em;
        }
        #${OVERLAY_ID} .auth-subtitle {
            margin: 9px 0 0;
            color: #b7c8dc;
            font-size: 14px;
            line-height: 1.5;
        }
        #${OVERLAY_ID} .auth-field { position: relative; margin-top: 16px; }
        #${OVERLAY_ID} label {
            display: block;
            margin-bottom: 7px;
            font-size: 12px;
            font-weight: 700;
            color: #cbd8e8;
        }
        #${OVERLAY_ID} input {
            width: 100%;
            box-sizing: border-box;
            padding: 13px 14px;
            border-radius: 12px;
            border: 1px solid rgba(148,163,184,.22);
            background: rgba(4,12,21,.72);
            color: #f8fbff;
            outline: none;
            font-size: 15px;
            transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
        }
        #${OVERLAY_ID} input:focus {
            border-color: rgba(102,167,255,.75);
            box-shadow: 0 0 0 3px rgba(102,167,255,.12);
            background: rgba(4,12,21,.9);
        }
        #${OVERLAY_ID} .auth-button {
            position: relative;
            width: 100%;
            margin-top: 22px;
            padding: 13px 16px;
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 12px;
            color: white;
            font-weight: 800;
            letter-spacing: .01em;
            cursor: pointer;
            background: linear-gradient(135deg, #10263d, #183a5d 38%, #1d4d7d 72%, #2a6bb1);
            box-shadow: 0 12px 25px rgba(15,23,42,.34), inset 0 1px 0 rgba(255,255,255,.13);
            transition: transform .18s ease, filter .18s ease;
        }
        #${OVERLAY_ID} .auth-button:hover { transform: translateY(-1px); filter: brightness(1.06); }
        #${OVERLAY_ID} .auth-button:disabled { opacity: .65; cursor: wait; transform: none; }
        #${OVERLAY_ID} .auth-error {
            min-height: 18px;
            margin-top: 12px;
            color: #ff8585;
            font-size: 12px;
            text-align: center;
        }
        #${SIGNOUT_ID} {
            position: fixed;
            top: 14px;
            right: 16px;
            z-index: 2147482000;
            display: none;
            border: 1px solid rgba(148,163,184,.22);
            border-radius: 999px;
            padding: 7px 12px;
            color: #dfeafc;
            background: rgba(8,18,29,.72);
            backdrop-filter: blur(10px);
            cursor: pointer;
            font: 600 12px/1 Inter, 'Segoe UI', sans-serif;
        }
        #${SIGNOUT_ID}:hover { background: rgba(102,167,255,.12); }
        body.auth-locked { overflow: hidden !important; }
        @media (max-width: 520px) {
            #${OVERLAY_ID} { padding: 16px; }
            #${OVERLAY_ID} .auth-card { padding: 27px 22px; border-radius: 20px; }
            #${OVERLAY_ID} .auth-title { font-size: 26px; }
            #${OVERLAY_ID} .auth-orbit { width: 310px; height: 310px; }
        }
    `;
    document.head.appendChild(style);

    function createOverlay() {
        let overlay = document.getElementById(OVERLAY_ID);
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = OVERLAY_ID;
        overlay.innerHTML = `
            <div class="auth-orbit" aria-hidden="true"></div>
            <div class="auth-card" role="dialog" aria-modal="true" aria-labelledby="auth-title">
                <div class="auth-brand">
                    <div class="auth-kicker">Private Financial Planning</div>
                    <h1 id="auth-title" class="auth-title">Parity Retirement Planner</h1>
                    <p class="auth-subtitle">Sign in to access your retirement projections, simulations and insights.</p>
                </div>
                <form id="auth-form" autocomplete="on">
                    <div class="auth-field">
                        <label for="auth-username">Username</label>
                        <input id="auth-username" name="username" type="text" autocomplete="username" required autofocus>
                    </div>
                    <div class="auth-field">
                        <label for="auth-password">Password</label>
                        <input id="auth-password" name="password" type="password" autocomplete="current-password" required>
                    </div>
                    <button id="auth-submit" class="auth-button" type="submit">Sign in securely</button>
                    <div id="auth-error" class="auth-error" role="alert" aria-live="polite"></div>
                </form>
            </div>
        `;
        document.body.appendChild(overlay);
        document.body.classList.add('auth-locked');
        return overlay;
    }

    function setLocked(locked) {
        const overlay = createOverlay();
        if (locked) {
            overlay.classList.remove('is-hidden');
            document.body.classList.add('auth-locked');
            const signout = document.getElementById(SIGNOUT_ID);
            if (signout) signout.style.display = 'none';
        } else {
            overlay.classList.add('is-hidden');
            document.body.classList.remove('auth-locked');
            const signout = document.getElementById(SIGNOUT_ID);
            if (signout) signout.style.display = 'block';
        }
    }

    function showError(message) {
        const el = document.getElementById('auth-error');
        if (el) el.textContent = message || '';
    }

    async function checkSession() {
        try {
            const response = await fetch('/auth/session', { credentials: 'same-origin', cache: 'no-store' });
            const data = await response.json();
            setLocked(!data.authenticated);
        } catch (_) {
            setLocked(true);
            showError('Unable to verify the session. Please try again.');
        }
    }

    async function login(event) {
        event.preventDefault();
        const username = document.getElementById('auth-username').value;
        const password = document.getElementById('auth-password').value;
        const button = document.getElementById('auth-submit');
        button.disabled = true;
        button.textContent = 'Signing in…';
        showError('');

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (!response.ok) {
                let message = 'Invalid username or password';
                try { message = (await response.json()).detail || message; } catch (_) {}
                throw new Error(message);
            }
            document.getElementById('auth-password').value = '';
            if (document.body.dataset.authGate === 'true') {
                window.location.reload();
                return;
            }
            setLocked(false);
        } catch (error) {
            showError(error.message || 'Unable to sign in.');
        } finally {
            if (document.body.dataset.authGate !== 'true') {
                button.disabled = false;
                button.textContent = 'Sign in securely';
            }
        }
    }

    function addSignout() {
        if (document.getElementById(SIGNOUT_ID)) return;
        const button = document.createElement('button');
        button.id = SIGNOUT_ID;
        button.type = 'button';
        button.textContent = 'Sign out';
        button.addEventListener('click', async () => {
            try {
                await fetch('/auth/logout', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' }
                });
            } finally {
                setLocked(true);
                document.getElementById('auth-password').value = '';
                showError('');
            }
        });
        document.body.appendChild(button);
    }

    function interceptProtectedFetch() {
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            const request = args[0];
            const url = typeof request === 'string' ? request : (request && request.url) || '';
            if (response.status === 401 && !url.includes('/auth/')) {
                setLocked(true);
                showError('Your session has expired. Please sign in again.');
            }
            return response;
        };
    }

    function init() {
        const overlay = createOverlay();
        overlay.querySelector('#auth-form').addEventListener('submit', login);
        addSignout();
        interceptProtectedFetch();
        checkSession();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
