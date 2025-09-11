from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.orm import validates
from ..database import Base

# Definimos la lista de valores permitidos
ESTADO_CONCILIACION_VALORES = [
    "GENERADA",
    "CANCELADO",
    "FINALIZADO"
]

class Conciliacion(Base):
    __tablename__ = "conciliacion"
    id_conciliacion = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    estado_conciliacion = Column(String(50), nullable=False)
    creado_en = Column(DateTime)
    @validates('estado_conciliacion')
    def validate_estado_conciliacion(self, key, value):
        assert value in ESTADO_CONCILIACION_VALORES, f"Valor inválido: {value}. Valores permitidos: {ESTADO_CONCILIACION_VALORES}"
        return value
