
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

# Asociación many-to-many Rol-Permiso
rol_permiso_association = Table(
    'rol_permiso_association', Base.metadata,
    Column('rol_id', Integer, ForeignKey('rol.id')),
    Column('permiso_id', Integer, ForeignKey('permiso.id'))
)

# Asociación many-to-many Usuario-Rol
usuario_rol_association = Table(
    'usuario_rol_association', Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuario.id')),
    Column('rol_id', Integer, ForeignKey('rol.id'))
)

# Asociación many-to-many Usuario-Permiso
usuario_permiso_association = Table(
    'usuario_permiso_association', Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuario.id')),
    Column('permiso_id', Integer, ForeignKey('permiso.id'))
)

class Rol(Base):
    __tablename__ = 'rol'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    permisos = relationship('Permiso', secondary=rol_permiso_association, back_populates='roles')
    usuarios = relationship('Usuario', secondary=usuario_rol_association, back_populates='roles')

class Permiso(Base):
    __tablename__ = 'permiso'
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(255))
    roles = relationship('Rol', secondary=rol_permiso_association, back_populates='permisos')
    usuarios = relationship('Usuario', secondary=usuario_permiso_association, back_populates='permisos')
