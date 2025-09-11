from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.oportunidad import Oportunidad as OportunidadModel
from ..schemas.oportunidad import Oportunidad, OportunidadCreate
from typing import List

router = APIRouter(prefix="/oportunidad", tags=["Oportunidad"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Oportunidad])
def read_oportunidades(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(OportunidadModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Oportunidad)
def create_oportunidad(oportunidad: OportunidadCreate, db: Session = Depends(get_db)):
    db_oportunidad = OportunidadModel(**oportunidad.dict())
    db.add(db_oportunidad)
    db.commit()
    db.refresh(db_oportunidad)
    return db_oportunidad

@router.get("/{oportunidad_id}", response_model=Oportunidad)
def get_oportunidad(oportunidad_id: int, db: Session = Depends(get_db)):
    oportunidad = db.query(OportunidadModel).filter(OportunidadModel.id_oportunidad == oportunidad_id).first()
    if not oportunidad:
        raise HTTPException(status_code=404, detail="Oportunidad not found")
    return oportunidad
