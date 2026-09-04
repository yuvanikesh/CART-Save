"""
CartGuard AI - Browser SDK (Python-side WebSocket handler)
This is the server-side counterpart to the browser CartGuard SDK.
"""
// CartGuard AI Browser SDK v2.0
// Inject via: <script src="cartguard-sdk.js" data-api="http://localhost:8000"></script>
// This file is served statically - it's the JavaScript Browser SDK

(function(window) {
  'use strict';

  const CartGuard = {
    config: {
      apiBase: document.currentScript?.dataset?.api || 'http://localhost:8000',
      sessionId: null,
      userId: null,
      throttleMs: 1000,
    },

    state: {
      sessionStart: Date.now(),
      events: [],
      mouseVelocity: 0,
      lastMouseX: 0,
      lastMouseY: 0,
      tabSwitches: 0,
      backButtonClicks: 0,
      scrollSpeed: 0,
      lastScrollY: 0,
      ws: null,
      scoring: false,
    },

    init(options = {}) {
      Object.assign(this.config, options);
      this.config.sessionId = options.sessionId || this._generateId();
      
      this._trackMouse();
      this._trackScroll();
      this._trackTab();
      this._trackHistory();
      this._connectWebSocket();
      
      console.log(`[CartGuard] SDK initialized. Session: ${this.config.sessionId}`);
      return this;
    },

    _generateId() {
      return 'SDK_' + Math.random().toString(36).substr(2, 9).toUpperCase();
    },

    _connectWebSocket() {
      const wsUrl = this.config.apiBase.replace('http', 'ws') + '/ws/' + this.config.sessionId;
      try {
        this.state.ws = new WebSocket(wsUrl);
        this.state.ws.onopen = () => console.log('[CartGuard] WebSocket connected');
        this.state.ws.onmessage = (e) => this._handleResult(JSON.parse(e.data));
        this.state.ws.onerror = () => console.warn('[CartGuard] WebSocket unavailable, using REST');
      } catch (e) {
        console.warn('[CartGuard] WebSocket init failed:', e);
      }
    },

    _trackMouse() {
      let lastTime = Date.now();
      document.addEventListener('mousemove', (e) => {
        const now = Date.now();
        const dt = (now - lastTime) / 1000;
        if (dt > 0) {
          const dx = e.clientX - this.state.lastMouseX;
          const dy = e.clientY - this.state.lastMouseY;
          this.state.mouseVelocity = Math.sqrt(dx*dx + dy*dy) / dt;
        }
        this.state.lastMouseX = e.clientX;
        this.state.lastMouseY = e.clientY;
        lastTime = now;

        // Detect exit intent (mouse near top of page)
        if (e.clientY < 50 && e.movementY < -5) {
          this._onExitIntent();
        }
      });
    },

    _trackScroll() {
      let lastScrollTime = Date.now();
      window.addEventListener('scroll', () => {
        const now = Date.now();
        const dt = (now - lastScrollTime) / 1000;
        const dy = Math.abs(window.scrollY - this.state.lastScrollY);
        this.state.scrollSpeed = dy / Math.max(dt, 0.1);
        this.state.lastScrollY = window.scrollY;
        lastScrollTime = now;
      });
    },

    _trackTab() {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.state.tabSwitches++;
          this._logEvent('TAB_SWITCH', { count: this.state.tabSwitches });
        }
      });
    },

    _trackHistory() {
      window.addEventListener('popstate', () => {
        this.state.backButtonClicks++;
        this._logEvent('BACK_NAVIGATION', { count: this.state.backButtonClicks });
      });
    },

    _onExitIntent() {
      this._logEvent('EXIT_INTENT', { mouseVelocity: this.state.mouseVelocity });
      this.scoreSession(); // Trigger immediate scoring on exit intent
    },

    _logEvent(type, data = {}) {
      this.state.events.push({
        type,
        timestamp: Date.now(),
        ...data,
      });

      if (this.state.ws?.readyState === WebSocket.OPEN) {
        this.state.ws.send(JSON.stringify({
          type: 'event',
          data: { event_type: type, ...data },
        }));
      }
    },

    // Public API
    trackCartAdd(product_id, price, quantity = 1) {
      this._logEvent('CART_ADD', { product_id, price, quantity });
    },

    trackCartRemove(product_id) {
      this._logEvent('CART_REMOVE', { product_id });
    },

    trackPaymentAttempt(method, success) {
      this._logEvent('PAYMENT_ATTEMPT', { method, success });
    },

    trackFormError(field) {
      this._logEvent('FORM_ERROR', { field });
    },

    scoreSession(extraData = {}) {
      if (this.state.scoring) return;
      this.state.scoring = true;

      const sessionData = {
        session_id: this.config.sessionId,
        session_duration: (Date.now() - this.state.sessionStart) / 1000,
        tab_switches: this.state.tabSwitches,
        back_navigations: this.state.backButtonClicks,
        ...extraData,
      };

      if (this.state.ws?.readyState === WebSocket.OPEN) {
        this.state.ws.send(JSON.stringify({ type: 'score_request', data: sessionData }));
      } else {
        fetch(`${this.config.apiBase}/api/v1/score`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sessionData),
        }).then(r => r.json()).then(result => {
          this._handleResult(result);
          this.state.scoring = false;
        }).catch(() => { this.state.scoring = false; });
      }
    },

    _handleResult(result) {
      this.state.scoring = false;
      const action = result?.action;
      if (!action || action.action_type === 'DO_NOTHING') return;

      // Show in-app nudge
      if (action.channel === 'IN_APP' && action.message) {
        this._showNudge(action);
      }

      // Fire callback if registered
      if (typeof this.config.onResult === 'function') {
        this.config.onResult(result);
      }

      console.log('[CartGuard] Result:', result);
    },

    _showNudge(action) {
      const existing = document.getElementById('cartguard-nudge');
      if (existing) existing.remove();

      const colors = {
        ALTERNATE_PAYMENT_GUIDANCE: '#0984e3',
        SOCIAL_PROOF_NUDGE: '#6c5ce7',
        CHECKOUT_ASSISTANCE: '#00b894',
        LIMITED_OFFER: '#e17055',
      };
      const color = colors[action.action_type] || '#667eea';

      const nudge = document.createElement('div');
      nudge.id = 'cartguard-nudge';
      nudge.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 99999;
        background: linear-gradient(135deg, #1a1f35, #252a45);
        border: 1px solid ${color}66;
        border-radius: 16px; padding: 20px 24px;
        max-width: 360px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        animation: cgSlideIn 0.4s ease; font-family: Inter, sans-serif;
        color: white;
      `;
      nudge.innerHTML = `
        <style>
          @keyframes cgSlideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }
        </style>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
          <span style="font-weight:700;font-size:14px;color:${color}">🛒 ${action.action_type.replace(/_/g,' ')}</span>
          <button onclick="document.getElementById('cartguard-nudge').remove()" 
            style="background:none;border:none;color:#999;cursor:pointer;font-size:18px;line-height:1;">×</button>
        </div>
        <p style="font-size:14px;line-height:1.5;color:#c8d0de;margin:0 0 12px;">
          ${action.message}
        </p>
        ${action.discount_amount > 0 ? `
          <div style="background:${color}22;border:1px solid ${color}44;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:13px;font-weight:600;color:${color};">
            💰 Save ₹${action.discount_amount} — Limited time!
          </div>
        ` : ''}
        <button onclick="document.getElementById('cartguard-nudge').remove()" 
          style="background:${color};color:white;border:none;border-radius:8px;padding:10px 20px;
          font-size:13px;font-weight:600;cursor:pointer;width:100%;">
          Got it →
        </button>
      `;
      document.body.appendChild(nudge);

      // Auto-dismiss after 30 seconds
      setTimeout(() => nudge?.remove(), 30000);
    },
  };

  window.CartGuard = CartGuard;
})(window);
