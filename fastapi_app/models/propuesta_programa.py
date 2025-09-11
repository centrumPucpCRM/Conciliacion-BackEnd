from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from ..database import Base

class PropuestaPrograma(Base):
    __tablename__ = "propuesta_programa"
    id_propuesta_programa = Column(Integer, primary_key=True, index=True)
    id_propuesta = Column(Integer, ForeignKey("propuesta.id_propuesta"))
    id_programa = Column(Integer, ForeignKey("programa.id_programa"))
