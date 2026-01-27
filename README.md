# Intranet - Sistema de Gestión de Empleados

Sistema web para gestión de empleados, vacaciones y actividades.

## Tecnologías

- **Backend**: Python 3.11+ con FastAPI
- **Frontend**: HTML, CSS, JavaScript (Jinja2 templates)
- **Base de datos**: PostgreSQL (Supabase)
- **Autenticación**: Supabase Auth + JWT
- **Reportes PDF**: ReportLab

## Estructura del Proyecto

```
intranet/
├── app/
│   ├── routers/           # Endpoints de la API
│   │   ├── auth.py        # Autenticación
│   │   ├── empleados.py   # Gestión de empleados
│   │   ├── vacaciones.py  # Módulo de vacaciones
│   │   ├── actividades.py # Registro de actividades
│   │   ├── catalogos.py   # Catálogos del sistema
│   │   ├── reportes.py    # Generación de PDFs
│   │   └── pages.py       # Rutas de páginas HTML
│   ├── services/          # Servicios
│   │   ├── pdf_generator.py  # Generador de reportes
│   │   └── email_service.py  # Envío de correos
│   ├── templates/         # Templates HTML (Jinja2)
│   │   ├── admin/         # Páginas de administrador
│   │   └── *.html         # Páginas de usuario
│   ├── static/            # Archivos estáticos
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   ├── main.py           # Aplicación principal
│   ├── config.py         # Configuración
│   ├── database.py       # Cliente de Supabase
│   ├── models.py         # Modelos Pydantic
│   ├── auth.py           # Utilidades de autenticación
│   └── scheduler.py      # Tareas programadas
├── requirements.txt
├── .env.example
└── README.md
```

## Instalación

1. Clonar el repositorio
2. Crear entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Copiar `.env.example` a `.env` y configurar variables
5. Ejecutar el script SQL en Supabase
6. Iniciar la aplicación:
   ```bash
   uvicorn app.main:app --reload
   ```

## Configuración de Supabase

1. Crear proyecto en [Supabase](https://supabase.com)
2. Ejecutar el script `intranet_schema.sql` en el SQL Editor
3. Obtener las credenciales:
   - URL del proyecto
   - Anon key (para el cliente público)
   - Service role key (para operaciones de admin)

## Variables de Entorno

```env
APP_NAME=Intranet
APP_ENV=development
DEBUG=true
SECRET_KEY=tu-clave-secreta

SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=tu-anon-key
SUPABASE_SERVICE_KEY=tu-service-role-key

RESEND_API_KEY=re_xxxxx  # Opcional, para correos
EMAIL_FROM=noreply@tuempresa.com

COMPANY_NAME=Tu Empresa S.A. de C.V.
```

## Módulos

### Usuario
- **Dashboard**: Vista general con perfil y accesos rápidos
- **Actividades**: Captura semanal de actividades (Lunes a Viernes)
- **Vacaciones**: Solicitud y seguimiento de vacaciones
- **Perfil**: Información personal

### Administrador
- **Dashboard Admin**: Estadísticas y alertas
- **Empleados**: Gestión de empleados
- **Vacaciones**: Aprobar/rechazar solicitudes
- **Reportes**: Generación de PDFs mensuales y semanales
- **Catálogos**: Gestión de puestos, supervisores, ubicaciones y proyectos

## API Endpoints

### Autenticación
- `POST /auth/login` - Iniciar sesión
- `POST /auth/logout` - Cerrar sesión

### Empleados
- `GET /api/empleados/me` - Mi perfil
- `GET /api/empleados/` - Listar empleados (admin)
- `POST /api/empleados/` - Crear empleado (admin)

### Vacaciones
- `GET /api/vacaciones/mis-solicitudes` - Mis solicitudes
- `POST /api/vacaciones/` - Nueva solicitud
- `GET /api/vacaciones/pendientes` - Pendientes (admin)
- `PATCH /api/vacaciones/{id}/aprobar` - Aprobar (admin)
- `PATCH /api/vacaciones/{id}/rechazar` - Rechazar (admin)

### Actividades
- `GET /api/actividades/semana` - Actividades de la semana
- `POST /api/actividades/semana` - Guardar semana completa
- `GET /api/actividades/admin/sin-captura` - Sin capturar (admin)

### Reportes
- `GET /api/reportes/mi-reporte-mensual/{anio}/{mes}` - Mi reporte PDF
- `GET /api/reportes/admin/reporte-mensual/{id}/{anio}/{mes}` - Reporte de empleado (admin)

### Catálogos
- `GET/POST/PATCH/DELETE /api/catalogos/puestos`
- `GET/POST/PATCH/DELETE /api/catalogos/supervisores`
- `GET/POST/PATCH/DELETE /api/catalogos/ubicaciones`
- `GET/POST/PATCH/DELETE /api/catalogos/proyectos`

## Tareas Programadas

- **Recordatorio semanal**: Viernes 10:00 AM - Envía recordatorio a empleados sin captura
- **Reset anual**: 1 de Enero - Reinicia días de vacaciones

## Licencia

Uso interno - Todos los derechos reservados
