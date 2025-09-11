"""
Inicialización de los modelos de la aplicación.
Este archivo controla el orden de importación para evitar problemas con las referencias circulares.
"""

# Primero importar los modelos base sin relaciones muchos-a-muchos
from .rol_permiso import Rol, Permiso, RolPermiso
from .cartera import Cartera
from .usuario import Usuario
from .usuario_cartera import UsuarioCartera  # Tabla intermedia
from .programa import Programa
from .oportunidad import Oportunidad
from .propuesta import Propuesta
from .tipo_cambio import TipoCambio
from .log import Log
from .conciliacion import Conciliacion
from .conciliacion_programa import ConciliacionPrograma
from .solicitud import Solicitud
from .propuesta_oportunidad import PropuestaOportunidad
from .propuesta_programa import PropuestaPrograma
from .solicitud_propuesta_oportunidad import SolicitudPropuestaOportunidad
from .solicitud_propuesta_programa import SolicitudPropuestaPrograma

# Otros modelos que puedan existir
