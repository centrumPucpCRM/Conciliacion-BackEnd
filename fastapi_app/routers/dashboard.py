from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.oportunidad import Oportunidad
from ..models.log import Log
from ..models.solicitud_x_oportunidad import SolicitudXOportunidad
from ..models.solicitud_x_programa import SolicitudXPrograma
import fastapi_app.models.solicitud
import fastapi_app.models.usuario

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard(db: Session = Depends(get_db)):
    # Header data
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

    # Log data (moved from /log/listar without pagination)
    logs_query = db.query(Log).order_by(Log.creadoEn.desc())
    logs = logs_query.all()

    # Preload all tipos de solicitud
    tipos_solicitud = db.query(fastapi_app.models.solicitud.TipoSolicitud).all()
    tipos_dict = {ts.id: ts.nombre for ts in tipos_solicitud}

    # Preload all valorSolicitud
    valores_solicitud = db.query(fastapi_app.models.solicitud.ValorSolicitud).all()
    valores_dict = {vs.id: vs.nombre for vs in valores_solicitud}

    # Preload all usuarios (for name lookup)
    usuarios = db.query(fastapi_app.models.usuario.Usuario).all()
    usuarios_dict = {u.id: u.nombre for u in usuarios}

    resultado = []
    for log in logs:
        sxos = db.query(SolicitudXOportunidad).filter_by(idSolicitud=log.idSolicitud).first()
        sxps = db.query(SolicitudXPrograma).filter_by(idSolicitud=log.idSolicitud).first()
        oportunidad = None
        programa = None
        if sxos:
            oportunidad = {
                "idOportunidad": sxos.idOportunidad,
                "montoPropuesto": sxos.montoPropuesto,
                "montoObjetado": sxos.montoObjetado
            }
        if sxps:
            programa = {
                "idPrograma": sxps.idPrograma,
                "fechaInaguracionPropuesta": sxps.fechaInaguracionPropuesta,
                "fechaInaguracionObjetada": sxps.fechaInaguracionObjetada
            }

        auditoria = log.auditoria.copy() if log.auditoria else {}
        # Enrich auditoria with usuario names if present, remove user IDs
        auditoria.pop("idUsuarioReceptor", None)
        auditoria.pop("idUsuarioGenerador", None)
        auditoria["nombreUsuarioReceptor"] = usuarios_dict.get(log.auditoria.get("idUsuarioReceptor")) if log.auditoria and log.auditoria.get("idUsuarioReceptor") else None
        auditoria["nombreUsuarioGenerador"] = usuarios_dict.get(log.auditoria.get("idUsuarioGenerador")) if log.auditoria and log.auditoria.get("idUsuarioGenerador") else None

        # Enrich auditoria with valorSolicitud name, remove valorSolicitud_id
        valor_id = log.auditoria.get("valorSolicitud_id") if log.auditoria else None
        auditoria.pop("valorSolicitud_id", None)
        auditoria["valorSolicitud"] = valores_dict.get(valor_id) if valor_id else None

        # Remove tipoSolicitud_id, only show nombre
        resultado.append({
            "id": log.id,
            "idSolicitud": log.idSolicitud,
            "tipoSolicitud": tipos_dict.get(log.tipoSolicitud_id),
            "creadoEn": log.creadoEn,
            "auditoria": auditoria,
            "oportunidad": oportunidad,
            "programa": programa
        })

    return {
        "header": {
            "propuestas": total_propuestas,
            "conciliaciones": 0,  # TODO: Reemplazar con conteo real más adelante
            "total_de_alumnos": total_oportunidades_recientes,
        },
        "log": {
            "items": resultado
        }
    }
