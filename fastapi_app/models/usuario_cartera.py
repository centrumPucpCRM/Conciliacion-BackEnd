from sqlalchemy import Column, Integer, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from ..database import Base

# Definir la tabla intermedia como objeto Table en lugar de clase
# Esto evita problemas con las referencias circulares
# Mantener la clase para posibles expansiones futuras
class UsuarioCartera(Base):
    __tablename__ = "usuario_cartera"  # Cambiamos el nombre para evitar conflicto
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))
    id_cartera = Column(Integer, ForeignKey("cartera.id_cartera"))
    fecha_vinculacion = Column(DateTime, nullable=True)
    # Otros campos para registrar cambios en la relación
