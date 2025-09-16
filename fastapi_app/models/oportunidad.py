from sqlalchemy import Column, Date, Integer, String, DateTime, Boolean, DECIMAL, ForeignKey
from ..database import Base

class Oportunidad(Base):
    __tablename__ = "oportunidad"
    id_oportunidad = Column(Integer, primary_key=True, index=True)
    id_programa = Column(Integer, ForeignKey("programa.id_programa"))
    nombre = Column(String(200), nullable=False)
    documento_identidad = Column(String(50), nullable=False)
    correo = Column(String(150))
    telefono = Column(String(50))
    etapa_venta = Column(String(80))
    moneda = Column(String(50))
    descuento = Column(DECIMAL(30,4))
    monto = Column(DECIMAL(30, 2))
    fecha_matricula = Column(Date)
    party_number = Column(String(50))
    conciliado = Column(Boolean, default=False)
    #Posibles calculados
    posible_atipico = Column(Boolean)
    becado = Column(Boolean)
    conciliado = Column(Boolean)
