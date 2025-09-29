
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.log import Log
from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
import fastapi_app.models.solicitud
import fastapi_app.models.usuario

router = APIRouter(prefix="/log", tags=["Log"])

@router.get("/listar")
def listar_logs_paginados(
	page: int = Query(1, ge=1, description="Página a consultar"),
	page_size: int = Query(20, ge=1, le=100, description="Cantidad de resultados por página"),
	db: Session = Depends(get_db)
):
	offset = (page - 1) * page_size
	logs_query = db.query(Log).order_by(Log.creadoEn.desc())
	total = logs_query.count()
	logs = logs_query.offset(offset).limit(page_size).all()

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
		"total": total,
		"page": page,
		"page_size": page_size,
		"items": resultado
	}
