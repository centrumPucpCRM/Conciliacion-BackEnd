
from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from .rol_permiso import usuario_rol_association, usuario_permiso_association

# Asociación Usuario-Cartera
usuario_cartera = Table(
    'usuario_cartera', Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuario.id')),
    Column('cartera_id', Integer, ForeignKey('cartera.id'))
)

class Usuario(Base):
    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    clave = Column(String(255))
    correo = Column(String(255))
    activo = Column(Boolean)
    roles = relationship('Rol', secondary=usuario_rol_association, back_populates='usuarios')
    permisos = relationship('Permiso', secondary=usuario_permiso_association, back_populates='usuarios')
    carteras = relationship('Cartera', secondary=usuario_cartera, back_populates='usuarios')