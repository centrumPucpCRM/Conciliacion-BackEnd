from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.oportunidad import Oportunidad

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard_header(db: Session = Depends(get_db)):
    total_propuestas = db.query(Propuesta).count()

    # Obtener la propuesta más reciente por fechaPropuesta (y por id como desempate)
    latest_propuesta = (
        db.query(Propuesta)
        .order_by(Propuesta.fechaPropuesta.desc(), Propuesta.id.desc())
        .first()
    )

    if latest_propuesta:
        total_oportunidades_recientes = (
            db.query(Oportunidad).filter(Oportunidad.idPropuesta == latest_propuesta.id).count()
        )
    else:
        total_oportunidades_recientes = 0

    return {
        "header": {
            "propuestas": total_propuestas,
            "conciliaciones": 0,  # TODO: Reemplazar con conteo real más adelante
            "total_de_alumnos": total_oportunidades_recientes,
        }
    }
