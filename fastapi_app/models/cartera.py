

from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from .usuario_cartera import usuario_cartera


class Cartera(Base):
    __tablename__ = 'cartera'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    usuarios = relationship('Usuario', secondary=usuario_cartera, back_populates='carteras')
