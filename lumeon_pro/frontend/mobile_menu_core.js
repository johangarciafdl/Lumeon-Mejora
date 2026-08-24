(() => {
  'use strict';

  const MOBILE_QUERY = '(max-width: 768px)';
  let openState = false;

  function sidebar() { return document.getElementById('sidebar'); }
  function button() { return document.getElementById('mobile-menu-button'); }
  function backdrop() { return document.getElementById('mobile-menu-backdrop'); }
  function isMobile() { return window.matchMedia?.(MOBILE_QUERY).matches === true; }

  function applyState(open) {
    const s = sidebar();
    const b = backdrop();
    const btn = button();
    openState = !!open;
    if (!s) return;

    s.classList.toggle('mobile-open', openState);
    s.setAttribute('aria-hidden', openState ? 'false' : 'true');

    if (isMobile()) {
      s.style.transform = openState ? 'translateX(0)' : 'translateX(-105%)';
      s.style.visibility = 'visible';
      s.style.pointerEvents = openState ? 'auto' : 'none';
      s.style.zIndex = '5000';
    } else {
      s.style.transform = '';
      s.style.visibility = '';
      s.style.pointerEvents = '';
      s.style.zIndex = '';
    }

    if (b) {
      b.classList.toggle('open', openState);
      b.setAttribute('aria-hidden', openState ? 'false' : 'true');
      if (isMobile() && openState) {
        b.style.display = 'block';
        b.style.opacity = '1';
        b.style.pointerEvents = 'auto';
        b.style.zIndex = '4999';
      } else {
        b.style.display = '';
        b.style.opacity = '';
        b.style.pointerEvents = '';
        b.style.zIndex = '';
      }
    }

    btn?.setAttribute('aria-expanded', openState ? 'true' : 'false');
    document.body.classList.toggle('mobile-menu-open', openState && isMobile());
    document.body.style.overflow = openState && isMobile() ? 'hidden' : '';
  }

  function toggle(event) {
    if (!isMobile()) return;
    event?.preventDefault();
    event?.stopPropagation();
    const s = sidebar();
    if (!s) return;
    applyState(!s.classList.contains('mobile-open'));
  }

  function close() { applyState(false); }
  function open() { applyState(true); }

  // Public API used by navigation_core. There is now exactly one source of
  // truth for the menu's open/closed state.
  window.openMobileMenu = open;
  window.closeMobileMenu = close;

  function ensure() {
    let btn = button();
    let b = backdrop();
    const topbar = document.getElementById('topbar');
    const title = document.getElementById('topbar-title');

    if (!btn && topbar && title) {
      btn = document.createElement('button');
      btn.id = 'mobile-menu-button';
      btn.type = 'button';
      btn.textContent = '☰';
      btn.setAttribute('aria-label', 'Abrir menú');
      btn.setAttribute('aria-expanded', 'false');
      topbar.insertBefore(btn, title);
    }

    if (!b) {
      b = document.createElement('div');
      b.id = 'mobile-menu-backdrop';
      b.setAttribute('aria-hidden', 'true');
      document.body.appendChild(b);
    }

    btn = button();
    b = backdrop();

    if (btn && !btn.dataset.lumeonMobileBound) {
      btn.dataset.lumeonMobileBound = '1';
      btn.style.pointerEvents = 'auto';
      btn.style.touchAction = 'manipulation';
      btn.style.position = 'relative';
      btn.style.zIndex = '5001';
      btn.addEventListener('click', toggle, false);
    }

    if (b && !b.dataset.lumeonMobileBound) {
      b.dataset.lumeonMobileBound = '1';
      b.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        close();
      }, false);
    }

    applyState(openState);
  }

  function boot() {
    ensure();
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });
    window.addEventListener('resize', () => {
      if (!isMobile()) close();
      else ensure();
    }, { passive: true });

    const observer = new MutationObserver(() => ensure());
    observer.observe(document.body, { childList: true, subtree: true });
    window.__lumeonMobileMenuObserver = observer;

    setTimeout(ensure, 100);
    setTimeout(ensure, 500);
    setTimeout(ensure, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
