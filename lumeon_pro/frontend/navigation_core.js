(() => {
  'use strict';

  const pages = [
    'dashboard',
    'inventario',
    'ventas',
    'clientes',
    'ciclos',
    'devoluciones',
    'admin-logs',
  ];

  const titles = {
    dashboard: 'Dashboard',
    inventario: 'Inventario',
    ventas: 'Ventas',
    clientes: 'Clientes',
    ciclos: 'Ciclos',
    devoluciones: 'Devoluciones',
    'admin-logs': 'Registros',
  };

  const topActions = {
    inventario: ['+ Nuevo Producto', 'openModalProducto'],
    ventas: ['+ Nueva Venta', 'openModalVenta'],
    clientes: ['+ Nuevo Cliente', 'openModalCliente'],
    devoluciones: ['+ Nueva Devolución', 'openModalDevolucion'],
  };

  function closeMobileMenu() {
    document.getElementById('sidebar')?.classList.remove('mobile-open');
    document.getElementById('mobile-menu-backdrop')?.classList.remove('open');
    document.body.style.overflow = '';
  }

  function pageElement(page) {
    return document.getElementById(`page-${page}`);
  }

  function setActiveNav(page) {
    document.querySelectorAll('#sidebar .nav-item').forEach((item) => {
      const onclick = item.getAttribute('onclick') || '';
      const match = onclick.match(/goto\((?:'|\")([^'\"]+)(?:'|\")\)/);
      const itemPage = match?.[1];
      item.classList.toggle('active', itemPage === page);
      if (page === 'admin-logs' && item.id === 'nav-registros') {
        item.classList.add('active');
      }
    });
  }

  function setTopbar(page) {
    const title = document.getElementById('topbar-title');
    if (title) title.textContent = titles[page] || 'Lumeon';

    const action = document.getElementById('topbar-action');
    if (!action) return;

    const spec = topActions[page];
    if (!spec) {
      action.style.display = 'none';
      action.onclick = null;
      return;
    }

    action.textContent = spec[0];
    action.style.display = 'flex';
    action.type = 'button';
    action.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      const fn = window[spec[1]];
      if (typeof fn === 'function') fn();
      else console.error(`Lumeon: no existe ${spec[1]}`);
    };
  }

  function loadPageData(page) {
    const loaders = {
      dashboard: 'loadDashboard',
      inventario: 'loadInventario',
      ventas: 'loadVentas',
      clientes: 'loadClientes',
      ciclos: 'loadCiclos',
      devoluciones: 'loadDevoluciones',
      'admin-logs': 'loadAdminLogs',
    };

    const fnName = loaders[page];
    if (!fnName) return;

    const fn = window[fnName];
    if (typeof fn !== 'function') {
      console.warn(`Lumeon: falta loader ${fnName}`);
      return;
    }

    Promise.resolve(fn()).catch((error) => {
      console.error(`Lumeon ${page} loader failed`, error);
      if (typeof window.toast === 'function') {
        window.toast(
          error?.message || `No se pudo cargar ${titles[page] || page}`,
          'error',
        );
      }
    });
  }

  function navigate(page) {
    if (!pages.includes(page)) return false;

    const target = pageElement(page);
    if (!target) return false;

    document.querySelectorAll('.page').forEach((p) => p.classList.remove('active'));
    target.classList.add('active');

    window.currentPage = page;
    setActiveNav(page);
    setTopbar(page);
    closeMobileMenu();

    window.scrollTo({ top: 0, behavior: 'auto' });
    const content = document.getElementById('content');
    if (content) content.scrollTop = 0;

    loadPageData(page);
    return true;
  }

  function bindMobileMenu() {
    let button = document.getElementById('mobile-menu-button');
    let backdrop = document.getElementById('mobile-menu-backdrop');

    if (!button) {
      button = document.createElement('button');
      button.id = 'mobile-menu-button';
      button.type = 'button';
      button.setAttribute('aria-label', 'Abrir menú');
      button.textContent = '☰';
      const topbar = document.getElementById('topbar');
      const title = document.getElementById('topbar-title');
      if (topbar && title) topbar.insertBefore(button, title);
    }

    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'mobile-menu-backdrop';
      document.body.appendChild(backdrop);
    }

    const open = () => {
      document.getElementById('sidebar')?.classList.add('mobile-open');
      backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    };

    button.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      const sidebar = document.getElementById('sidebar');
      if (sidebar?.classList.contains('mobile-open')) closeMobileMenu();
      else open();
    };

    backdrop.onclick = closeMobileMenu;
  }

  function expose() {
    window.goto = navigate;
    window.navigateLumeon = navigate;
    window.closeMobileMenu = closeMobileMenu;
  }

  function start() {
    expose();
    bindMobileMenu();

    const active = document.querySelector('.page.active');
    const page = active?.id?.startsWith('page-')
      ? active.id.slice(5)
      : 'dashboard';

    window.currentPage = page;
    setActiveNav(page);
    setTopbar(page);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
