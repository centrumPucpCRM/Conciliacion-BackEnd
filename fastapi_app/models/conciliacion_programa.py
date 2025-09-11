from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from ..database import Base

class ConciliacionPrograma(Base):
    __tablename__ = "conciliacion_programa"
    id_conciliacion_programa = Column(Integer, primary_key=True, index=True)
    id_conciliacion = Column(Integer, ForeignKey("conciliacion.id_conciliacion"), unique=True)
    pago_proyectado = Column(DECIMAL(18, 2), nullable=True)
