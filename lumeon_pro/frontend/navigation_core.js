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
    window.closeMobileMenu?.();
    document.getElementById('sidebar')?.classList.remove('mobile-open');
    document.getElementById('mobile-menu-backdrop')?.classList.remove('open');
    document.body.classList.remove('mobile-menu-open');
    document.body.style.overflow = '';
  }

  function pageElement(page) {
    return document.getElementById(`page-${page}`);
  }

  function extractPage(item) {
    const direct = item?.dataset?.page;
    if (direct && pages.includes(direct)) return direct;

    const onclick = item?.getAttribute('onclick') || '';
    const match = onclick.match(/goto\((?:'|")([^'"]+)(?:'|")\)/);
    return match?.[1] || '';
  }

  function setActiveNav(page) {
    document.querySelectorAll('#sidebar .nav-item').forEach((item) => {
      item.classList.toggle('active', extractPage(item) === page);
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

    const fn = window[loaders[page]];
    if (typeof fn !== 'function') return;

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

    try {
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch {
      window.scrollTo(0, 0);
    }

    const content = document.getElementById('content');
    if (content) content.scrollTop = 0;

    loadPageData(page);
    return true;
  }

  function bindNavItems() {
    document.querySelectorAll('#sidebar .nav-item').forEach((item) => {
      const page = extractPage(item);
      if (!pages.includes(page)) return;

      item.dataset.page = page;

      if (item.dataset.lumeonNavBound === '1') return;
      item.dataset.lumeonNavBound = '1';

      item.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        navigate(page);
      }, false);
    });
  }

  function bindAdminLogs() {
    const item = document.getElementById('nav-registros');
    if (!item || item.dataset.lumeonLogsBound === '1') return;

    item.dataset.lumeonLogsBound = '1';
    item.dataset.page = 'admin-logs';

    item.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      navigate('admin-logs');
    }, false);
  }

  function expose() {
    window.goto = navigate;
    window.navigateLumeon = navigate;
    window.closeMobileMenu = closeMobileMenu;
  }

  function start() {
    expose();
    bindNavItems();
    bindAdminLogs();

    const active = document.querySelector('.page.active');
    const page = active?.id?.startsWith('page-')
      ? active.id.slice(5)
      : 'dashboard';

    window.currentPage = page;
    setActiveNav(page);
    setTopbar(page);

    // Cargar los datos de la página activa también en el arranque.
    // Esto evita que la interfaz aparezca vacía después de una recarga.
    loadPageData(page);

    setTimeout(() => {
      expose();
      bindNavItems();
      bindAdminLogs();

      const activePage = window.currentPage || page;
      setActiveNav(activePage);
      setTopbar(activePage);
      loadPageData(activePage);
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
