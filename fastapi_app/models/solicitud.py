from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class TipoSolicitud(Base):
    __tablename__ = 'tipo_solicitud'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), unique=True)

class ValorSolicitud(Base):
    __tablename__ = 'valor_solicitud'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), unique=True)

class Solicitud(Base):
    __tablename__ = 'solicitud'
    id = Column(Integer, primary_key=True, index=True)
    idUsuarioReceptor = Column(Integer, ForeignKey('usuario.id'))
    idUsuarioGenerador = Column(Integer, ForeignKey('usuario.id'))
    abierta = Column(Boolean, default=True)
    tipoSolicitud_id = Column(Integer, ForeignKey('tipo_solicitud.id'))
    valorSolicitud_id = Column(Integer, ForeignKey('valor_solicitud.id'))
    comentario = Column(String(255))
    creadoEn = Column(DateTime)
    tipoSolicitud = relationship('TipoSolicitud')
    valorSolicitud = relationship('ValorSolicitud')
