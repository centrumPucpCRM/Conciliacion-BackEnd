from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Cartera(Base):
    __tablename__ = "cartera"
    id_cartera = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), unique=True, nullable=False)
    descripcion = Column(String(255), nullable=True)

    # Relación muchos-a-muchos con Usuario usando la tabla usuario_cartera
    usuarios = relationship(
        "Usuario",
        secondary="usuario_cartera",
        back_populates="carteras",
        lazy="joined"  # Optimización para cargar relaciones
    )
