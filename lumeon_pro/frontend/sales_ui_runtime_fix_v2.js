(() => {
  'use strict';

  // Stable runtime loader. The previous V2 implementation contained
  // overlapping navigation/sales handlers. Keep one canonical runtime.
  const src = document.createElement('script');
  src.src = '/sales_ui_runtime_fix_v4.js';
  src.defer = false;
  document.head.appendChild(src);
})();
