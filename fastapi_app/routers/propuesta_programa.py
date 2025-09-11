from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.propuesta_programa import PropuestaPrograma as PropuestaProgramaModel
from ..schemas.propuesta_programa import PropuestaPrograma, PropuestaProgramaCreate
from typing import List

router = APIRouter(prefix="/propuesta_programa", tags=["PropuestaPrograma"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[PropuestaPrograma])
def read_propuesta_programas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PropuestaProgramaModel).offset(skip).limit(limit).all()

@router.post("/", response_model=PropuestaPrograma)
def create_propuesta_programa(propuesta_programa: PropuestaProgramaCreate, db: Session = Depends(get_db)):
    db_propuesta_programa = PropuestaProgramaModel(**propuesta_programa.dict())
    db.add(db_propuesta_programa)
    db.commit()
    db.refresh(db_propuesta_programa)
    return db_propuesta_programa

@router.get("/{propuesta_programa_id}", response_model=PropuestaPrograma)
def get_propuesta_programa(propuesta_programa_id: int, db: Session = Depends(get_db)):
    propuesta_programa = db.query(PropuestaProgramaModel).filter(PropuestaProgramaModel.id_propuesta_programa == propuesta_programa_id).first()
    if not propuesta_programa:
        raise HTTPException(status_code=404, detail="PropuestaPrograma not found")
    return propuesta_programa
