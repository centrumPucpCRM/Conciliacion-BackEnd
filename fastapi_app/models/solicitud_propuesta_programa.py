from sqlalchemy import Column, Integer, ForeignKey
from ..database import Base

class SolicitudPropuestaPrograma(Base):
    __tablename__ = "solicitud_propuesta_programa"
    id = Column(Integer, primary_key=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"))
    id_propuesta_programa = Column(Integer, ForeignKey("propuesta_programa.id_propuesta_programa"))
