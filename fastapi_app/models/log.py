from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DECIMAL, DateTime
from ..database import Base

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base

class Log(Base):
    __tablename__ = 'log'
    id = Column(Integer, primary_key=True, index=True)
    idSolicitud = Column(Integer, ForeignKey('solicitud.id'))
    auditoria = Column(JSON)
    tipoSolicitud_id = Column(Integer, ForeignKey('tipo_solicitud.id'))
    creadoEn = Column(DateTime)
    solicitud = relationship('Solicitud')
    tipoSolicitud = relationship('TipoSolicitud')
