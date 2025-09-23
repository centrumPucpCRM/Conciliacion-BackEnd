from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from ..database import Base

class ConciliacionPrograma(Base):
    __tablename__ = "conciliacion_programa"
    id = Column(Integer, primary_key=True, index=True)
    id_conciliacion = Column(Integer, ForeignKey("conciliacion.id"), unique=True)
    pago_proyectado = Column(DECIMAL(18, 2), nullable=True)
