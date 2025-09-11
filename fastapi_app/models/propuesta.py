from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, CheckConstraint
from sqlalchemy.orm import validates
from ..database import Base

# Definimos las listas de valores permitidos
TIPO_PROPUESTA_VALORES = ["CREACION", "MODIFICACION", "OTRO", "NUEVO_VALOR"]
ESTADO_PROPUESTA_VALORES = ["GENERADA", "CANCELADO", "PRECONCILIADA", "APROBACION", "CONCILIADA", "PROGRAMADA"]

class Propuesta(Base):
    __tablename__ = "propuesta"
    id_propuesta = Column(Integer, primary_key=True, index=True)
    id_conciliacion = Column(Integer, ForeignKey("conciliacion.id_conciliacion"), nullable=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(String(800), nullable=True)
    tipo_propuesta = Column(String(50), nullable=False)
    estado_propuesta = Column(String(50), nullable=False)
    creado_en = Column(DateTime)
    
    @validates('tipo_propuesta')
    def validate_tipo_propuesta(self, key, value):
        assert value in TIPO_PROPUESTA_VALORES, f"Valor inválido: {value}. Valores permitidos: {TIPO_PROPUESTA_VALORES}"
        return value
        
    @validates('estado_propuesta')
    def validate_estado_propuesta(self, key, value):
        assert value in ESTADO_PROPUESTA_VALORES, f"Valor inválido: {value}. Valores permitidos: {ESTADO_PROPUESTA_VALORES}"
        return value
