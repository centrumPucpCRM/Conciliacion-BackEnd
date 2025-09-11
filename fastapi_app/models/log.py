from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DECIMAL, DateTime
from ..database import Base

class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"))
    id_propuesta = Column(Integer, ForeignKey("propuesta.id_propuesta"), nullable=True)
    id_usuario_generador = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    id_usuario_receptor = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    aceptado_por_responsable = Column(Boolean, nullable=True)
    tipo_solicitud = Column(String(30), nullable=True)
    valor_solicitud = Column(String(30), nullable=True)
    comentario = Column(String(800), nullable=True)
    id_propuesta_programa = Column(Integer, ForeignKey("propuesta_programa.id_propuesta_programa"), nullable=True)
    id_propuesta_oportunidad = Column(Integer, ForeignKey("propuesta_oportunidad.id_propuesta_oportunidad"), nullable=True)
    monto_propuesto = Column(DECIMAL(18, 2), nullable=True)
    monto_objetado = Column(DECIMAL(18, 2), nullable=True)
    fecha_creacion = Column(DateTime)
