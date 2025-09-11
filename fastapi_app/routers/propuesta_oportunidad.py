from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from ..models.propuesta_oportunidad import PropuestaOportunidad as PropuestaOportunidadModel
from ..schemas.propuesta_oportunidad import PropuestaOportunidad, PropuestaOportunidadCreate
from typing import List

router = APIRouter(prefix="/propuesta_oportunidad", tags=["PropuestaOportunidad"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[PropuestaOportunidad])
def read_propuesta_oportunidades(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PropuestaOportunidadModel).offset(skip).limit(limit).all()

@router.post("/", response_model=PropuestaOportunidad)
def create_propuesta_oportunidad(propuesta_oportunidad: PropuestaOportunidadCreate, db: Session = Depends(get_db)):
    db_propuesta_oportunidad = PropuestaOportunidadModel(**propuesta_oportunidad.dict())
    db.add(db_propuesta_oportunidad)
    db.commit()
    db.refresh(db_propuesta_oportunidad)
    return db_propuesta_oportunidad

@router.get("/{propuesta_oportunidad_id}", response_model=PropuestaOportunidad)
def get_propuesta_oportunidad(propuesta_oportunidad_id: int, db: Session = Depends(get_db)):
    propuesta_oportunidad = db.query(PropuestaOportunidadModel).filter(PropuestaOportunidadModel.id_propuesta_oportunidad == propuesta_oportunidad_id).first()
    if not propuesta_oportunidad:
        raise HTTPException(status_code=404, detail="PropuestaOportunidad not found")
    return propuesta_oportunidad

# Endpoint para actualizar cualquier campo de PropuestaOportunidad por id
@router.patch("/{id_propuesta_oportunidad}")
def update_propuesta_oportunidad(id_propuesta_oportunidad: int, fields: dict = Body(...), db: Session = Depends(get_db)):
    propuesta_op = db.query(PropuestaOportunidadModel).filter(PropuestaOportunidadModel.id_propuesta_oportunidad == id_propuesta_oportunidad).first()
    if not propuesta_op:
        raise HTTPException(status_code=404, detail="PropuestaOportunidad no encontrada")
    for key, value in fields.items():
        if hasattr(propuesta_op, key):
            setattr(propuesta_op, key, value)
    db.commit()
    db.refresh(propuesta_op)
    return propuesta_op
