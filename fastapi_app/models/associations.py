from sqlalchemy import Column, ForeignKey, Integer, Table
from ..database import Base

usuario_cartera = Table(
    "usuario_cartera",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuario.id"), primary_key=True),
    Column("cartera_id", Integer, ForeignKey("cartera.id"), primary_key=True)
)

# Association table for Propuesta <-> Cartera
propuesta_cartera = Table(
    "propuesta_cartera",
    Base.metadata,
    Column("propuesta_id", Integer, ForeignKey("propuesta.id"), primary_key=True),
    Column("cartera_id", Integer, ForeignKey("cartera.id"), primary_key=True)
)
