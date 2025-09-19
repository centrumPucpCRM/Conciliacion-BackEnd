from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..database import get_db
from ..utils.csv_loader import process_csv_data

router = APIRouter(tags=["CSV Upload"])

class PropuestaPayload(BaseModel):
    nombre: Optional[str] = Field(None, description="Nombre sugerido para la propuesta")
    fecha: Optional[str] = Field(None, description="Fecha y hora asociada a la conciliacion")
    carteras: List[str] = Field(default_factory=list, description="Carteras seleccionadas para la conciliacion")

class CsvUploadPayload(BaseModel):
    propuesta: Optional[PropuestaPayload] = None
    csv_url: Optional[str] = Field(
        default=None,
        description="URL directa del archivo CSV de conciliacion (por ejemplo, en S3)"
    )
    detalle: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Datos de conciliacion convertidos manualmente a JSON (compatibilidad)"
    )

    class Config:
        extra = "allow"

example_payload = {
    "propuesta": {
        "nombre": "Propuesta_2024-05-01_08",
        "fecha": "2024-05-01T08:00",
        "carteras": ["Cartera A", "Cartera B"]
    },
    "csv_url": "https://centrum-conciliacion-service.s3.us-east-1.amazonaws.com/CONCILIACION_2024-05-01+8AM.csv"
}

@router.post(
    "/upload-conciliacion-csv/",
    response_model=Dict[str, Any],
    description="Procesa datos de conciliacion recibidos mediante una URL de CSV o un listado JSON"
)
async def upload_conciliacion_csv(
    payload: CsvUploadPayload = Body(..., example=example_payload),
    db: Session = Depends(get_db)
):
    """
    Endpoint para procesar conciliaciones a partir de un CSV disponible via URL.
    Tambien acepta un arreglo JSON (detalle) por compatibilidad con integraciones anteriores.
    """
    try:
        result = await process_csv_data(db, payload.dict(exclude_none=True))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar los datos: {str(e)}")
