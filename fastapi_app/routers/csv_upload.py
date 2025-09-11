from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import json

from ..database import get_db
from ..utils.csv_loader import process_csv_data

router = APIRouter(tags=["CSV Upload"])

# Modelo para la documentación con ejemplos
class ConciliacionItem(BaseModel):
    class Config:
        extra = "allow"  # Permite campos adicionales

# Ejemplo de datos para la documentación
example_data = [
    {
        "usuario.nombre": "Juan Perez",
        "cartera.nombre": "Cartera A",
        "programa.codigo": "PROG001",
        "programa.nombre": "MBA Ejecutivo",
        "programa.fecha_de_inicio": "01/01/2023",
        "programa.fecha_de_inauguracion": "15/01/2023",
        "programa.fecha_ultima_postulante": "30/06/2023",
        "programa.moneda": "EUR",
        "programa.precio_lista": 25000,
        "oportunidad.nombre": "Ana Rodriguez",
        "oportunidad.documento_identidad": "12345678",
        "oportunidad.correo": "ana.rodriguez@ejemplo.com",
        "oportunidad.telefono": "987654321",
        "oportunidad.etapa_venta": "Inscrito",
        "oportunidad.descuento": 0.3333,
        "oportunidad.moneda": "PEN",
        "oportunidad.monto": 22500,
        "oportunidad.becado": True,
        "oportunidad.conciliado": False
    },
    {
        "usuario.nombre": "Juan Perez",
        "cartera.nombre": "Cartera A",
        "programa.codigo": "PROG001",
        "programa.nombre": "MBA Ejecutivo",
        "programa.fecha_de_inicio": "01/01/2023",
        "programa.fecha_de_inauguracion": "15/01/2023",
        "programa.fecha_ultima_postulante": "30/06/2023",
        "programa.moneda": "PEN",
        "programa.precio_lista": 25000,
        "oportunidad.nombre": "Ana Rodriguez 2",
        "oportunidad.documento_identidad": "12345678 2",
        "oportunidad.correo": "ana.rodriguez@ejemplo.com2",
        "oportunidad.telefono": "9876543212",
        "oportunidad.etapa_venta": "Inscrito",
        "oportunidad.descuento": 0.3330,
        "oportunidad.moneda": "PEN",
        "oportunidad.monto": 22500,
        "oportunidad.becado": True,
        "oportunidad.conciliado": False
    },
    {
        "usuario.nombre": "Juan Perez",
        "cartera.nombre": "Cartera A",
        "programa.codigo": "PROG001",
        "programa.nombre": "MBA Ejecutivo",
        "programa.fecha_de_inicio": "01/01/2023",
        "programa.fecha_de_inauguracion": "15/01/2023",
        "programa.fecha_ultima_postulante": "30/06/2023",
        "programa.moneda": "PEN",
        "programa.precio_lista": 25000,
        "oportunidad.nombre": "Ana Rodriguez 3",
        "oportunidad.documento_identidad": "123456783",
        "oportunidad.correo": "ana.rodriguez@ejemplo.com3",
        "oportunidad.telefono": "987654321 3",
        "oportunidad.etapa_venta": "Inscrito",
        "oportunidad.descuento": 0.3300,
        "oportunidad.moneda": "PEN",
        "oportunidad.monto": 22500,
        "oportunidad.becado": True,
        "oportunidad.conciliado": False
    },
    {
        "usuario.nombre": "Maria Lopez",
        "cartera.nombre": "Cartera B",
        "programa.codigo": "PROG002",
        "programa.nombre": "Maestría en Data Science",
        "programa.fecha_de_inicio": "15/02/2023",
        "programa.fecha_de_inauguracion": "01/03/2023",
        "programa.fecha_ultima_postulante": "15/07/2023",
        "programa.moneda": "USD",
        "programa.precio_lista": 15000,
        "oportunidad.nombre": "Carlos Gomez",
        "oportunidad.documento_identidad": "87654321",
        "oportunidad.correo": "carlos.gomez@ejemplo.com",
        "oportunidad.telefono": "123456789",
        "oportunidad.etapa_venta": "Interesado",
        "oportunidad.descuento": 0.3000,
        "oportunidad.moneda": "USD",
        "oportunidad.monto": 14250,
        "oportunidad.becado": False,
        "oportunidad.conciliado": False

    }
]

@router.post(
    "/upload-conciliacion-csv/", 
    response_model=Dict[str, Any],
    description="Procesa datos de conciliación en formato JSON que han sido convertidos desde un CSV"
)
async def upload_conciliacion_csv(
    data: List[Dict[str, Any]] = Body(..., example=example_data),
    db: Session = Depends(get_db)
):
    """
    Endpoint para procesar datos CSV de conciliación en formato JSON.
    El cliente puede convertir el CSV a JSON y enviarlo directamente.
    
    Los datos deben tener un formato específico con campos para usuarios, carteras, programas y oportunidades.
    
    Ejemplo de formato:
    ```json
    [
        {
            "usuario.nombre": "Juan Perez",
            "cartera.nombre": "Cartera A",
            "programa.codigo": "PROG001",
            ...
        },
        {
            "usuario.nombre": "Maria Lopez",
            "cartera.nombre": "Cartera B",
            "programa.codigo": "PROG002",
            ...
        }
    ]
    ```
    """
    try:
        result = await process_csv_data(db, data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar los datos: {str(e)}")

