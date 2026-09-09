# OdontoSmart

Sistema de gestión odontológica multi-empresa desarrollado en Django para clínicas y consultorios dentales.

## Características

- Gestión de empresas y multi-tenancy
- Administración de usuarios, roles y permisos
- Registro y control de pacientes
- Agendamiento de citas
- Gestión de médicos y especialidades
- Historias clínicas y odontograma
- Reportes y panel de control
- Facturación y documentación SRI
- Integración con procesos de validación y firma XML

## Stack

- Python
- Django
- SQLite por defecto
- Bootstrap 5
- Pillow, OpenPyXL, requests, lxml, cryptography

## Requisitos

- Python 3.10+
- pip
- Git

## Instalación

1. Clona el repositorio:

```bash
git clone git@github.com:jurdin32/OdontoSmart.git
cd OdontoSmart
```

2. Crea y activa un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

4. Configura variables de entorno:

```bash
cp .env.example .env
```

Edita `.env` si necesitas personalizar la clave secreta, debug y hosts permitidos.

5. Ejecuta migraciones:

```bash
python manage.py migrate
```

6. Crea un superusuario:

```bash
python manage.py createsuperuser
```

7. Inicia el servidor:

```bash
python manage.py runserver
```

Abre la aplicación en:

```text
http://127.0.0.1:8000
```

## Estructura principal

```text
OdontoSmart/
├── core/              # lógica central, permisos, tenant, tareas
├── usuarios/          # autenticación y administración de usuarios
├── pacientes/         # pacientes
├── medicos/           # médicos y especialidades
├── citas/             # agenda y citas
├── historias/         # historias clínicas y odontograma
├── facturacion/       # facturación y documentos
├── reportes/          # reportes y dashboard
├── sri/               # procesos del SRI, XML y validación
├── templates/         # plantillas HTML
├── static/            # recursos estáticos
├── media/             # archivos generados por usuarios
├── manage.py          # entrada de Django
├── requirements.txt    # dependencias del proyecto
├── .env.example       # variables de entorno de ejemplo
├── .gitignore         # archivos ignorados por Git
└── README.md
```

## Variables de entorno

Ejemplo disponible en `.env.example`:

```env
DJANGO_SECRET_KEY=change-me-por-una-clave-aleatoria-larga
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
```

## Comandos útiles

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
python manage.py test
```

## Nota

Este proyecto usa SQLite por defecto para facilitar desarrollo local. Para producción se recomienda revisar la configuración de seguridad, secret key, hosts y base de datos.
