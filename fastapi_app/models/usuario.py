from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario = Column(Integer, primary_key=True, index=True)
    dni = Column(String(20), nullable=True)
    correo = Column(String(120), unique=True, nullable=False)
    nombres = Column(String(150), nullable=False)
    celular = Column(String(30), nullable=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)

    # Relación con el modelo Rol
    rol = relationship("Rol", back_populates="usuarios")

    # Relación muchos-a-muchos con Cartera
    carteras = relationship(
        "Cartera",
        secondary="usuario_cartera",
        back_populates="usuarios",
        lazy="joined"  # Optimización para cargar relaciones
    )