(() => {
  'use strict';

  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });

  const start = () =>
    loadScript('/sales_ui_runtime_fix_v8.js?v=20260824-4')
      .then(() => loadScript('/navigation_core.js?v=20260824-5'))
      .then(() => loadScript('/mobile_menu_core.js?v=20260824-1'))
      .catch((error) => console.error('Lumeon frontend runtime failed', error));

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
