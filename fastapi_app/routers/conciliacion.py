from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.conciliacion import Conciliacion as ConciliacionModel
from ..schemas.conciliacion import Conciliacion, ConciliacionCreate
from typing import List

router = APIRouter(prefix="/conciliacion", tags=["Conciliacion"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Conciliacion])
def read_conciliaciones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(ConciliacionModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Conciliacion)
def create_conciliacion(conciliacion: ConciliacionCreate, db: Session = Depends(get_db)):
    db_conciliacion = ConciliacionModel(**conciliacion.dict())
    db.add(db_conciliacion)
    db.commit()
    db.refresh(db_conciliacion)
    return db_conciliacion

@router.get("/{conciliacion_id}", response_model=Conciliacion)
def get_conciliacion(conciliacion_id: int, db: Session = Depends(get_db)):
    conciliacion = db.query(ConciliacionModel).filter(ConciliacionModel.id_conciliacion == conciliacion_id).first()
    if not conciliacion:
        raise HTTPException(status_code=404, detail="Conciliacion not found")
    return conciliacion
