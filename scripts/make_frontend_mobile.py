from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "lumeon_pro" / "frontend"
INDEX = ROOT / "index.html"
ASSISTANT = ROOT / "assistant.css"

MOBILE_CSS = r'''
/* =========================================================
   LUMEON PRO - MOBILE RESPONSIVE LAYOUT
   ========================================================= */
#mobile-menu-btn{display:none}
#mobile-menu-overlay{display:none}

@media (max-width: 768px){
  html,body{width:100%;min-width:0;overflow-x:hidden}
  body{display:block;font-size:14px}

  #sidebar{
    width:280px;
    max-width:88vw;
    min-height:100vh;
    height:100dvh;
    transform:translateX(-105%);
    transition:transform .22s ease;
    box-shadow:12px 0 36px rgba(0,0,0,.22);
  }
  #sidebar.mobile-open{transform:translateX(0)}
  #mobile-menu-overlay{
    position:fixed;
    inset:0;
    background:rgba(10,15,20,.48);
    backdrop-filter:blur(2px);
    z-index:99;
  }
  #mobile-menu-overlay.open{display:block}

  #main{margin-left:0;width:100%;min-width:0}
  #topbar{
    height:auto;
    min-height:58px;
    padding:10px 14px;
    gap:10px;
  }
  #mobile-menu-btn{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    width:40px;
    height:40px;
    flex:0 0 40px;
    padding:0;
    border:1px solid var(--border);
    border-radius:var(--radius);
    background:var(--bg2);
    color:var(--ink);
    font-size:22px;
    cursor:pointer;
  }
  .page-title{font-size:18px;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #topbar-right{gap:8px;min-width:0}
  #topbar-action{padding:9px 11px;white-space:nowrap}

  #content{padding:16px 12px 88px;width:100%;min-width:0}
  .page-header{display:block;margin-bottom:18px}
  .page-header-left h2{font-size:24px}
  .page-header-left p{font-size:11px}

  .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:16px}
  .kpi-card{padding:16px 13px}
  .kpi-value{font-size:23px}
  .kpi-label{font-size:9px;letter-spacing:1px}
  .kpi-sub{font-size:10px}

  .two-col{grid-template-columns:1fr;gap:12px}
  .card{padding:15px;margin-bottom:12px}
  .card-header{margin-bottom:14px;padding-bottom:12px}
  .card-title{font-size:15px}
  .card-subtitle{font-size:10px}

  .table-wrap{overflow-x:visible}
  table{font-size:12px}
  th{font-size:9px;padding:9px 8px}
  td{padding:10px 8px}

  /* Convert dense data tables into horizontally scrollable cards only when needed. */
  #page-inventario .table-wrap,
  #page-ventas .table-wrap,
  #page-clientes .table-wrap,
  #page-devoluciones .table-wrap,
  #page-dashboard .table-wrap,
  .items-table-wrap{
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
  }
  #page-inventario table,
  #page-ventas table,
  #page-clientes table,
  #page-devoluciones table,
  #page-dashboard table,
  .items-table-wrap table{
    min-width:680px;
  }

  .form-grid,.form-grid.cols3{grid-template-columns:1fr}
  .form-group.full{grid-column:auto}
  .modal-overlay{padding:8px}
  .modal,.modal-xl{
    width:100%;
    max-width:none;
    max-height:calc(100dvh - 16px);
    margin:0;
  }
  .modal-header{padding:15px 16px}
  .modal-body{padding:16px}
  .modal-footer{padding:13px 16px;flex-wrap:wrap}
  .modal-footer .btn{flex:1 1 140px;justify-content:center}

  .search-bar{max-width:none;width:100%;flex:1 1 100%}
  .tabs{overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch}
  .tab{padding:10px 13px}

  .ciclo-header{padding:15px 14px;gap:12px;align-items:flex-start}
  .ciclo-name{font-size:16px}
  .ciclo-meta{font-size:10px}
  .ciclo-stats{gap:12px;flex-wrap:wrap;justify-content:flex-end}
  .ciclo-stat-val{font-size:16px}
  .ciclo-stat-label{font-size:8px}
  .ciclo-body{padding:15px}

  .prod-row{gap:10px}
  .prod-name{font-size:12px;min-width:0}

  .btn{min-height:40px;padding:9px 13px}
  .btn-sm{min-height:36px;padding:7px 10px}

  #toast{left:10px;right:10px;bottom:76px}
  .toast-item{min-width:0;width:100%}

  /* Sale modal: keep the product entry controls easy to tap. */
  #vf-ref{width:100%!important;flex:1 1 100%!important}
  #vf-cant{width:100%!important;flex:1 1 100%!important}

  /* Make the assistant sit above the mobile bottom area. */
  #lumeon-assistant,.lumeon-assistant{
    right:8px!important;
    left:8px!important;
    bottom:8px!important;
    width:auto!important;
    height:min(78dvh,680px)!important;
  }
  #lumeon-assistant-fab,.la-fab{right:16px!important;bottom:72px!important}
}

@media (max-width: 430px){
  .kpi-grid{grid-template-columns:1fr 1fr}
  .kpi-card{padding:14px 10px}
  .kpi-value{font-size:21px}
  .page-header-left h2{font-size:22px}
  #topbar-action{font-size:10px;padding:8px 9px}
}
'''

MOBILE_BUTTON = '''    <button id="mobile-menu-btn" type="button" aria-label="Abrir menú" aria-expanded="false" onclick="toggleMobileMenu()">☰</button>\n'''
OVERLAY = '<div id="mobile-menu-overlay" onclick="closeMobileMenu()"></div>\n'
JS = r'''

function toggleMobileMenu(){
  const sidebar=document.getElementById('sidebar');
  const overlay=document.getElementById('mobile-menu-overlay');
  const btn=document.getElementById('mobile-menu-btn');
  if(!sidebar||!overlay||!btn) return;
  const open=!sidebar.classList.contains('mobile-open');
  sidebar.classList.toggle('mobile-open',open);
  overlay.classList.toggle('open',open);
  btn.setAttribute('aria-expanded',String(open));
}

function closeMobileMenu(){
  const sidebar=document.getElementById('sidebar');
  const overlay=document.getElementById('mobile-menu-overlay');
  const btn=document.getElementById('mobile-menu-btn');
  sidebar?.classList.remove('mobile-open');
  overlay?.classList.remove('open');
  btn?.setAttribute('aria-expanded','false');
}
'''

text = INDEX.read_text(encoding="utf-8")

if "/* LUMEON PRO - MOBILE RESPONSIVE LAYOUT */" not in text:
    text = text.replace("</style>", MOBILE_CSS + "\n</style>", 1)

if 'id="mobile-menu-btn"' not in text:
    text = text.replace(
        '  <div id="topbar">\n    <span class="page-title"',
        '  <div id="topbar">\n' + MOBILE_BUTTON + '    <span class="page-title"',
        1,
    )

if 'id="mobile-menu-overlay"' not in text:
    text = text.replace('</aside>\n<main id="main">', '</aside>\n' + OVERLAY + '<main id="main">', 1)

if "function toggleMobileMenu()" not in text:
    text = text.replace("function goto(page){", JS + "\nfunction goto(page){", 1)

# Close the mobile drawer whenever navigation changes.
if "closeMobileMenu();\n  const titles=" not in text:
    text = text.replace(
        "  const titles={dashboard:'Dashboard',inventario:'Inventario',ventas:'Ventas',clientes:'Clientes',ciclos:'Ciclos',devoluciones:'Devoluciones'};",
        "  closeMobileMenu();\n  const titles={dashboard:'Dashboard',inventario:'Inventario',ventas:'Ventas',clientes:'Clientes',ciclos:'Ciclos',devoluciones:'Devoluciones'};",
        1,
    )

INDEX.write_text(text, encoding="utf-8")

if ASSISTANT.exists():
    atext = ASSISTANT.read_text(encoding="utf-8")
    extra = '''\n@media (max-width: 768px){\n  #lumeon-assistant-fab,.la-fab{bottom:72px;right:16px}\n  #lumeon-assistant,.lumeon-assistant{\n    left:8px!important;right:8px!important;bottom:8px!important;width:auto!important;\n    height:min(78dvh,680px)!important;\n  }\n  .la-header{padding:14px 15px}\n  .la-messages{padding:12px}\n  .la-msg{max-width:92%;font-size:13px}\n  .la-composer{padding:10px}\n  .la-input{font-size:16px;min-height:42px}\n  .la-send{min-width:48px;min-height:42px}\n}\n'''
    if "height:min(78dvh,680px)" not in atext:
        atext += extra
        ASSISTANT.write_text(atext, encoding="utf-8")

print("MOBILE RESPONSIVE FRONTEND UPDATED")
print("Desktop layout preserved.")
print("Mobile sidebar, topbar, forms, modals, tables, dashboard and assistant adjusted.")
print("No database was touched.")
