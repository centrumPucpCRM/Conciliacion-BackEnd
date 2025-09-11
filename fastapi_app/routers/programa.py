from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.programa import Programa as ProgramaModel
from ..schemas.programa import Programa, ProgramaCreate
from typing import List

router = APIRouter(prefix="/programa", tags=["Programa"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Programa])
def read_programas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(ProgramaModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Programa)
def create_programa(programa: ProgramaCreate, db: Session = Depends(get_db)):
    db_programa = ProgramaModel(**programa.dict())
    db.add(db_programa)
    db.commit()
    db.refresh(db_programa)
    return db_programa

@router.get("/{programa_id}", response_model=Programa)
def get_programa(programa_id: int, db: Session = Depends(get_db)):
    programa = db.query(ProgramaModel).filter(ProgramaModel.id_programa == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa not found")
    return programa
