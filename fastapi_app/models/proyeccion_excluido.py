from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from ..database import Base


class ProyeccionExcluido(Base):
    """
    Leads de proyección (FFC / Interés / Admisión) excluidos manualmente por programa.

    Estos leads vienen del CRM en vivo (no son filas de `oportunidad`), así que para
    "eliminarlos" de la proyección se guarda su leadNumber aquí y se filtran tanto en
    el modal de proyectados como en el conteo de Fijo Fuera de Counter.
    """
    __tablename__ = 'proyeccion_excluido'
    id = Column(Integer, primary_key=True)
    idPrograma = Column(Integer, ForeignKey('programa.id'), index=True)
    leadNumber = Column(String(255), index=True)
    creadoEn = Column(DateTime, default=datetime.now)
