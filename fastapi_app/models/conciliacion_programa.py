from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from ..database import Base

class ConciliacionPrograma(Base):
    __tablename__ = "conciliacion_programa"
    id = Column(Integer, primary_key=True, index=True)
    id_conciliacion = Column(Integer, ForeignKey("conciliacion.id"), unique=True)
    # Refencia del programa MESCAMBIADO.,etc
    # Calcular el MontoReal.    #Precalculados cuando se pasa una propuesta a estado Conciliado
    # Calcular el alumnos real. #Precalculados cuando se pasa una propuesta a estado Conciliado
    pago_proyectado = Column(DECIMAL(18, 2), nullable=True)
    # AlumnosProyectado #EL JP va poder editar esto
    # MontoProyectado #El JP va poder editar esto
        
