# Conciliación API

Este proyecto implementa una API REST para un sistema de conciliación utilizando Django y Django REST Framework.

## Requisitos

- Python 3.8+
- Django 4.2.4
- Django REST Framework 3.14.0
- MySQL 8.0+

## Instalación

1. Clonar el repositorio:
```bash
git clone <URL_del_repositorio>
cd Conciliacion/Backend
```

2. Crear un entorno virtual:
```bash
python -m venv env
```

3. Activar el entorno virtual:
```bash
# En Windows
env\Scripts\activate

# En Unix o MacOS
source env/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. La configuración de la base de datos ya está lista en `backend/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'conciliacion',
           'USER': 'root',
           'PASSWORD': 'A@ndre240200',
           'HOST': 'localhost',
           'PORT': '3306',
           'OPTIONS': {
               'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
           },
       }
   }
   ```

6. La base de datos "conciliacion" ya existe en MySQL.

7. Generar migraciones y aplicarlas (usando --fake-initial para no alterar las tablas existentes):
```bash
python manage.py makemigrations
python manage.py migrate --fake-initial
```

8. Crear un superusuario:
```bash
python manage.py createsuperuser
```

9. Iniciar el servidor:
```bash
python manage.py runserver
```

> **NOTA**: Hemos utilizado `--fake-initial` para que Django no intente crear tablas que ya existen en la base de datos. Esto permite que Django reconozca las tablas existentes sin intentar modificarlas.

## Estructura del proyecto

- `backend/`: Configuración principal del proyecto Django
- `crud_api/`: Aplicación principal con modelos, vistas y serializadores
  - `models.py`: Definición de modelos de datos
  - `views.py`: Vistas para la API REST
  - `serializers.py`: Serializadores para los modelos
  - `urls.py`: Definición de rutas para la API

## API Endpoints

La API proporciona endpoints CRUD para todos los modelos del sistema:

- `/api/tipos-solicitud/`
- `/api/valores-solicitud/`
- `/api/estados-propuesta/`
- `/api/tipos-propuesta/`
- `/api/estados-conciliacion/`
- `/api/roles/`
- `/api/permisos/`
- `/api/roles-permisos/`
- `/api/carteras/`
- `/api/usuarios/`
- `/api/programas/`
- `/api/oportunidades/`
- `/api/tipos-cambio/`
- `/api/conciliaciones/`
- `/api/conciliaciones-programas/`
- `/api/propuestas/`
- `/api/propuestas-programas/`
- `/api/propuestas-oportunidades/`
- `/api/solicitudes/`
- `/api/solicitudes-propuestas-programas/`
- `/api/solicitudes-propuestas-oportunidades/`
- `/api/logs/`

Cada endpoint soporta operaciones GET, POST, PUT y DELETE.

## Autenticación

El sistema utiliza autenticación básica de Django REST Framework. Para acceder a la API, se debe incluir el token de autenticación en las cabeceras de las peticiones HTTP.
