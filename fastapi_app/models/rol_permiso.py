from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Rol(Base):
    __tablename__ = "rol"
    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    
    # Relación con la tabla Usuario
    usuarios = relationship("Usuario", back_populates="rol")

class Permiso(Base):
    __tablename__ = "permiso"
    id_permiso = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(200), unique=True, nullable=False)

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class RolPermiso(Base):
    __tablename__ = "rol_permiso"
    id = Column(Integer, primary_key=True, index=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)
    id_permiso = Column(Integer, ForeignKey("permiso.id_permiso"), nullable=False)

    rol = relationship("Rol", backref="rol_permisos")
    permiso = relationship("Permiso", backref="rol_permisos")
