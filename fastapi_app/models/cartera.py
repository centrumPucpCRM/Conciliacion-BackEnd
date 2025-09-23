from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base
from .associations import usuario_cartera, propuesta_cartera

class Cartera(Base):
    __tablename__ = 'cartera'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    usuarios = relationship('Usuario', secondary=usuario_cartera, back_populates='carteras')
    propuestas = relationship('Propuesta', secondary=propuesta_cartera, back_populates='carteras')
