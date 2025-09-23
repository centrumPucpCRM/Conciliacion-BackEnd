from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Date
from ..database import Base

class TipoCambio(Base):
    __tablename__ = "tipo_cambio"
    id = Column(Integer, primary_key=True, index=True)
    moneda_origen = Column(String(10))
    moneda_target = Column(String(10))
    equivalencia = Column(DECIMAL(18, 6))
    creado_en = Column(DateTime)
    fecha_tipo_cambio = Column(Date, nullable=True)
