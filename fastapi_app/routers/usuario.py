from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.usuario import Usuario as UsuarioModel
from ..schemas.usuario import Usuario, UsuarioCreate
from typing import List

router = APIRouter(prefix="/usuario", tags=["Usuario"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Usuario])
def read_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(UsuarioModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Usuario)
def create_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = UsuarioModel(**usuario.dict())
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.get("/{usuario_id}", response_model=Usuario)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario not found")
    return usuario
