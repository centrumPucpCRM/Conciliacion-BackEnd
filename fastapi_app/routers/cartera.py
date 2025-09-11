from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.cartera import Cartera as CarteraModel
from ..schemas.cartera import Cartera, CarteraCreate
from typing import List

router = APIRouter(prefix="/cartera", tags=["Cartera"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Cartera])
def read_carteras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(CarteraModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Cartera)
def create_cartera(cartera: CarteraCreate, db: Session = Depends(get_db)):
    db_cartera = CarteraModel(**cartera.dict())
    db.add(db_cartera)
    db.commit()
    db.refresh(db_cartera)
    return db_cartera

@router.get("/{cartera_id}", response_model=Cartera)
def get_cartera(cartera_id: int, db: Session = Depends(get_db)):
    cartera = db.query(CarteraModel).filter(CarteraModel.id_cartera == cartera_id).first()
    if not cartera:
        raise HTTPException(status_code=404, detail="Cartera not found")
    return cartera
