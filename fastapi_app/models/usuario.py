from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..database import Base
from .associations import usuario_cartera
from .rol_permiso import usuario_rol_association, usuario_permiso_association


class Usuario(Base):
    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    clave = Column(String(255))
    documentoIdentidad = Column(String(50), unique=True)
    correo = Column(String(255))
    activo = Column(Boolean)
    roles = relationship('Rol', secondary=usuario_rol_association, back_populates='usuarios')
    permisos = relationship('Permiso', secondary=usuario_permiso_association, back_populates='usuarios')
    carteras = relationship('Cartera', secondary=usuario_cartera, back_populates='usuarios')