"""
Configuración y constantes para el módulo de subdirecciones.
Centraliza la configuración de permisos y mapeos de usuarios.
"""

# Usuarios con acceso total a todas las subdirecciones del sistema
USUARIOS_ACCESO_TOTAL = [
    "daf.supervisor",
    "daf.subdirector",
    "admin"
]

# Mapeo de usuarios específicos a sus subdirecciones asignadas
MAPEO_USUARIOS_SUBDIRECCIONES = {
    "Jefe grado": ["Grado"],
    "Jefe ee": ["Educacion Ejecutiva"],
    "Jefe CentrumX": ["CentrumX"]
}

