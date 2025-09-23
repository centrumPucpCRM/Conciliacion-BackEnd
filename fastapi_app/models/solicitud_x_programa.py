from sqlalchemy import Column, Integer, Date, ForeignKey
from fastapi_app.database import Base

class SolicitudXPrograma(Base):
    __tablename__ = 'solicitud_x_programa'
    id = Column(Integer, primary_key=True)
    idPrograma = Column(Integer, ForeignKey('programa.id'))
    idSolicitud = Column(Integer, ForeignKey('solicitud.id'))
    fechaInaguracionPropuesta = Column(Date)
    fechaInaguracionObjetada = Column(Date)