from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DateTime
from sqlalchemy.orm import validates
from ..database import Base

# Definimos las listas de valores permitidos
TIPO_SOLICITUD_VALORES = [
    "EXCLUSION_PROGRAMA",
    "ELIMINACION_BECADO",
    "EDICION_ALUMNO",
    "AGREGAR_ALUMNO",
    "APROBACION_JP"
    "APROBACION_COMERCIAL",
    "APROBACION_DAF"
]

VALOR_SOLICITUD_VALORES = [
    "ACEPTADO",
    "RECHAZADO",
    "PENDIENTE"
]

class Solicitud(Base):
    __tablename__ = "solicitud"
    id_solicitud = Column(Integer, primary_key=True, index=True)
    id_propuesta = Column(Integer, ForeignKey("propuesta.id_propuesta"))
    id_usuario_generador = Column(Integer, ForeignKey("usuario.id_usuario"))
    id_usuario_receptor = Column(Integer, ForeignKey("usuario.id_usuario"))
    aceptado_por_responsable = Column(Boolean, default=False)
    tipo_solicitud = Column(String(50), nullable=False)
    valor_solicitud = Column(String(50), nullable=False)
    comentario = Column(String(800), nullable=True)
    creado_en = Column(DateTime)
    abierta = Column(Boolean, default=True  )
    @validates('tipo_solicitud')
    def validate_tipo_solicitud(self, key, value):
        assert value in TIPO_SOLICITUD_VALORES, f"Valor inválido: {value}. Valores permitidos: {TIPO_SOLICITUD_VALORES}"
        return value
        
    @validates('valor_solicitud')
    def validate_valor_solicitud(self, key, value):
        assert value in VALOR_SOLICITUD_VALORES, f"Valor inválido: {value}. Valores permitidos: {VALOR_SOLICITUD_VALORES}"
        return value
