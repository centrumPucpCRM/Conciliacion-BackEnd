from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.oportunidad import Oportunidad
from ..models.log import Log
from ..routers.log import enrich_log_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_header(db: Session) -> dict:
    """Helper function to get dashboard header data"""
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
        "propuestas": total_propuestas,
        "conciliaciones": 0,  # TODO: Reemplazar con conteo real más adelante
        "total_de_alumnos": total_oportunidades_recientes,
    }


def get_recent_logs(db: Session, limit: int = 5) -> list:
    """Helper function to get recent logs with enrichment"""
    logs_query = db.query(Log).order_by(Log.creadoEn.desc())
    logs = logs_query.limit(limit).all()
    return enrich_log_data(logs, db)


@router.get("/")
def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard data including header statistics and recent logs"""
    header_data = get_dashboard_header(db)
    recent_logs = get_recent_logs(db, limit=5)

    return {
        "header": header_data,
        "log": recent_logs
    }
