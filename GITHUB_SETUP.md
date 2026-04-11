# 📋 INSTRUCCIONES: Subir LUMEON PRO a GitHub

## Opción 1: Crear Repositorio Nuevo (Recomendado)

### Paso 1: Inicializar Git localmente

```bash
cd C:\Users\johan\Downloads\LUMEON_PRO_SOFTWARE
git init
git add .
git commit -m "Initial commit: LUMEON PRO - Sistema de Gestión Natura & Avon"
```

### Paso 2: Crear Repositorio en GitHub

1. Ve a [https://github.com/new](https://github.com/new)
2. Nombre: `lumeon-pro`
3. Descripción: `Sistema de Gestión de Ventas y Recibos Automáticos para Natura & Avon`
4. Selecciona: Public (o Private si lo prefieres)
5. **NO** inicialices con README (ya tenemos uno)
6. Click en "Create repository"

### Paso 3: Conectar y Publicar

```bash
git remote add origin https://github.com/TU_USUARIO/lumeon-pro.git
git branch -M main
git push -u origin main
```

**Nota:** Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub.

---

## Opción 2: Si ya existe un repositorio

```bashbash
cd C:\Users\johan\Downloads\LUMEON_PRO_SOFTWARE
git add .
git commit -m "Update: Sistema de correos automáticos completamente implementado"
git push
```

---

## 📦 Contenido que se subirá

```text
lumeon-pro/
├── .venv/                          (ignorado ✓)
├── .env                            (ignorado ✓)
├── .gitignore                      (nuevo)
├── README.md
├── requirements.txt
├── lumeon_pro/
│   ├── backend/
│   │   ├── app.py                  (CORREOS AUTOMÁTICOS ✓)
│   │   ├── database.db             (ignorado ✓)
│   │   └── static/
│   ├── frontend/
│   │   ├── index.html
│   │   └── styles/
│   ├── .env                        (ignorado ✓)
│   ├── .env.example                (configuración)
│   ├── start_server.bat
│   ├── test_email_system.py
│   └── requirements.txt
├── CONFIGURAR_GMAIL.md
├── RECIBOS_AUTOMATICOS.md
├── IMPLEMENTACION_COMPLETADA.md
├── INICIO_RAPIDO_RECIBOS.md
└── EJEMPLO_RECIBO_VISUAL.html
```

---

## ⚠️ IMPORTANTE

- **NO subas `.env` con credenciales** ✓ (ya está en .gitignore)
- **NO subas `database.db`** ✓ (ya está en .gitignore)
- **NO subas `.venv/`** ✓ (ya está en .gitignore)
- Usa `.env.example` como referencia

---

## 🚀 Después de Publicar

Para clonar el repositorio en otra máquina:

```bash
git clone https://github.com/TU_USUARIO/lumeon-pro.git
cd lumeon-pro
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📝 Próximos Commits Sugeridos

```bash
# Después de cambios
git add .
git commit -m "Feature: [descripción del cambio]"
git push

# Ejemplos:
git commit -m "Feature: Add WhatsApp notifications"
git commit -m "Fix: Email encoding issues"
git commit -m "Docs: Update installation guide"
```

---

## 🔗 Enlaces Útiles

- **GitHub CLI Installation:** [https://cli.github.com/](https://cli.github.com/)
- **Git Documentation:** [https://git-scm.com/doc](https://git-scm.com/doc)
- **GitHub Guides:** [https://guides.github.com/](https://guides.github.com/)
