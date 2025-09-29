
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..utils import process_csv_data
from ..database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PropuestaPayload:
    def __init__(self, nombre: str, fecha: str = None, carteras: list = None):
        self.nombre = nombre
        self.fecha = fecha
        self.carteras = carteras or []

@router.post("/procesar-csv", summary="Procesa conciliación desde CSV", tags=["CSV Loader"])
async def procesar_csv_endpoint(
    body: dict = Body(
        ...,
        example={
            "propuesta": {
                "nombre": "nombrePropuesta",
                "carteras": [
                    "In Company",
                    "EE Estrategia, Gestión y Talento",
                    "EE Operaciones, Supply y Proyectos",
                    "EE Alta Dirección",
                    "Executive - Tiempo completo",
                    "MBA Centrum",
                    "Perú - Regiones (Grado)",
                    "Maestria Especializada Sectoriales",
                    "Maestria Especializada Core",
                    "EE Finanzas, Contabilidad y Gestión de Riesgos",
                    "EE Marketing, Ventas y Comercial",
                    "EE Tecnología, Innovación y Agile",
                    "EE EdEx",
                    "EE Sectoriales",
                    "MADEN"
                ]
            },
            "fechaDatos": "2025-09-16",
            "horaDatos": "11AM"
        },
        description="JSON con los datos de la propuesta y la URL pública del archivo CSV a procesar"
    ),
    db: Session = Depends(get_db)
):
    try:
        resultado = process_csv_data(db, body)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
