from sqlalchemy import Column, Integer, ForeignKey, DECIMAL, String
from ..database import Base

class PropuestaOportunidad(Base):
    __tablename__ = "propuesta_oportunidad"
    id_propuesta_oportunidad = Column(Integer, primary_key=True, index=True)
    id_propuesta = Column(Integer, ForeignKey("propuesta.id_propuesta"))
    id_oportunidad = Column(Integer, ForeignKey("oportunidad.id_oportunidad"))
    id_propuesta_programa = Column(Integer, ForeignKey("propuesta_programa.id_propuesta_programa"), nullable=True)
    id_tipo_cambio = Column(Integer, ForeignKey("tipo_cambio.id_tipo_cambio"), nullable=True)
    monto_propuesto = Column(DECIMAL(18, 2), nullable=True)
    etapa_venta_propuesto = Column(String(400), nullable=True)
