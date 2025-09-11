from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.log import Log as LogModel
from ..schemas.log import Log, LogCreate
from typing import List

router = APIRouter(prefix="/log", tags=["Log"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Log])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(LogModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Log)
def create_log(log: LogCreate, db: Session = Depends(get_db)):
    db_log = LogModel(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{log_id}", response_model=Log)
def get_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(LogModel).filter(LogModel.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
