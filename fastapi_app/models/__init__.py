"""
Inicialización de los modelos de la aplicación.
Este archivo controla el orden de importación para evitar problemas con las referencias circulares.
"""
# ...existing code...
from .programa import Programa
from .oportunidad import Oportunidad
from .propuesta import Propuesta
from .tipo_cambio import TipoCambio
from .log import Log
from .conciliacion import Conciliacion
from .conciliacion_programa import ConciliacionPrograma
from .solicitud import Solicitud

# Otros modelos que puedan existir
