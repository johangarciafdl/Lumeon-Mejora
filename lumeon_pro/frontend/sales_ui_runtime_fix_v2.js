(() => {
  'use strict';

  // Carga secuencial: primero Ventas y después el núcleo de navegación.
  // Así ningún runtime anterior puede sobrescribir goto() después de instalarlo.
  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });

  const start = () =>
    loadScript('/sales_ui_runtime_fix_v8.js?v=20260824-3')
      .then(() => loadScript('/navigation_core.js?v=20260824-2'))
      .catch((error) => console.error('Lumeon frontend runtime failed', error));

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
