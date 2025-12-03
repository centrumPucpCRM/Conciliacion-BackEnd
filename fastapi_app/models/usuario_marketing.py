from sqlalchemy import Column, Integer, String, BigInteger, Boolean, JSON, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class UsuarioMarketing(Base):
    __tablename__ = 'usuario_marketing'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    party_id = Column(BigInteger, nullable=False, index=True)
    party_number = Column(String(50), nullable=False)
    correo = Column(String(150), nullable=False, index=True)
    vacaciones = Column(Boolean, nullable=False, default=False)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=True, index=True)
    dias_pendientes = Column(JSON, nullable=True)
    periodos = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relación con la tabla usuario
    usuario = relationship('Usuario', foreign_keys=[id_usuario])
    
    # Índice único compuesto para party_id + party_number
    __table_args__ = (
        UniqueConstraint('party_id', 'party_number', name='idx_unique_party_id_number'),
    )
