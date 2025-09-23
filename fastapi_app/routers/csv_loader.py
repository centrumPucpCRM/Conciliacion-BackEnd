
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
                "fecha": "2025-09-22",
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
            "csv_url": "https://centrum-conciliacion-service.s3.us-east-1.amazonaws.com/CONCILIACION_2025-06-16+2PM.csv"
        },
        description="JSON con los datos de la propuesta y la URL pública del archivo CSV a procesar"
    ),
    db: Session = Depends(get_db)
):
    """
    Procesa conciliación desde un archivo CSV remoto. El archivo debe tener las columnas esperadas.
    Ejemplo de uso en Swagger:
    {
      "propuesta": {
        "nombre": "nombrePropuesta",
        "fecha": "2025-09-22",
        "carteras": ["Cartera 1", "Cartera 2"]
      },
      "csv_url": "https://ejemplo.com/archivo.csv"
    }
    """
    try:
        resultado = process_csv_data(db, body)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
