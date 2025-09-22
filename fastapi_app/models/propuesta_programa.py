from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class PropuestaPrograma(Base):
    __tablename__ = 'propuesta_programa'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    # Agrega aquí los campos y relaciones necesarios según tu modelo
