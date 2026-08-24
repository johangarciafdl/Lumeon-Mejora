(() => {
  'use strict';

  async function syncSalesAdminRole() {
    try {
      const response = await fetch('/api/v2/auth/me', {
        credentials: 'same-origin',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || !body.ok || !body.authenticated) return;

      const role = String(body.role || body.user?.role || '').toLowerCase();
      window.currentUser = {
        username: body.username || body.user?.username || String(body.user_id || ''),
        role,
        user_id: body.user_id,
      };
      window.lumeonIsAdmin = role === 'admin';

      document.querySelectorAll('.admin-only-nav').forEach(el => {
        el.style.display = role === 'admin' ? '' : 'none';
      });

      const page = document.getElementById('page-ventas');
      if (page?.classList.contains('active')) {
        window.loadVentas?.();
      }

      /* One predictable action layout on desktop and mobile. */
      if (!document.getElementById('lumeon-sales-action-style')) {
        const style = document.createElement('style');
        style.id = 'lumeon-sales-action-style';
        style.textContent = `
          .sales-actions{display:flex!important;align-items:center;gap:4px;flex-wrap:wrap}
          .sales-actions .btn{flex:0 0 auto}
          .sales-payment-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--border)}
          .sales-payment-meta{font-size:10px;color:var(--ink3);margin-top:3px}
          .sales-payment-totals{display:flex;justify-content:space-between;margin-top:7px;font-size:12px}
          @media(max-width:768px){.sales-actions{justify-content:flex-end;width:100%!important}.sales-actions .btn{min-height:34px!important;padding:6px 8px!important;font-size:10px!important}.sales-payment-row{font-size:11px}}
        `;
        document.head.appendChild(style);
      }
    } catch (error) {
      console.debug('Lumeon admin role sync unavailable', error);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncSalesAdminRole, { once: true });
  } else {
    syncSalesAdminRole();
  }
})();
