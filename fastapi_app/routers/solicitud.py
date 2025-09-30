from fastapi import Query

from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma

from fastapi import Body, HTTPException

from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])
# Endpoint generico para crear solicitudes de alumno o programa
@router.post("/crear")
def crear_solicitud_generica(
	body: dict = Body(...),
	db: Session = Depends(get_db)
):
	tipo_solicitud = body.get("tipo_solicitud") #OBLIGATORIO
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"]:
		if tipo_solicitud == "AGREGAR_ALUMNO":
			# Validar campos obligatorios
			required_fields = ["idPrograma", "idOportunidad", "idUsuarioGenerador", "comentario"]
			for field in required_fields:
				if body.get(field) is None:
					raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

			id_programa = body["idPrograma"]
			id_oportunidad = body["idOportunidad"]
			id_usuario_generador = body["idUsuarioGenerador"]
			comentario = body["comentario"]

			# Obtener programa para idPropuesta y idUsuarioReceptor
			from fastapi_app.models.programa import Programa
			programa = db.query(Programa).filter_by(id=id_programa).first()
			if not programa:
				raise HTTPException(status_code=400, detail="Programa no encontrado")
			id_propuesta = programa.idPropuesta
			id_usuario_receptor = programa.idJefeProducto

			# Obtener tipoSolicitud_id
			from fastapi_app.models.solicitud import TipoSolicitud, ValorSolicitud
			tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre=tipo_solicitud).first()
			if not tipo_solicitud_obj:
				raise HTTPException(status_code=400, detail="TipoSolicitud no encontrado")
			tipo_solicitud_id = tipo_solicitud_obj.id

			# Obtener valorSolicitud_id para "ABIERTA"
			valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="ABIERTA").first()
			if not valor_solicitud_obj:
				raise HTTPException(status_code=400, detail="ValorSolicitud 'ABIERTA' no encontrado")
			valor_solicitud_id = valor_solicitud_obj.id

			# Crear la solicitud
			solicitud = SolicitudModel(
				idUsuarioReceptor=id_usuario_receptor,
				idUsuarioGenerador=id_usuario_generador,
				tipoSolicitud_id=tipo_solicitud_id,
				valorSolicitud_id=valor_solicitud_id,
				idPropuesta=id_propuesta,
				comentario=comentario,
				abierta=True
			)
			db.add(solicitud)
			db.commit()
			db.refresh(solicitud)

			# Crear la relación en solicitud_x_oportunidad
			monto_propuesto = body.get("montoPropuesto")
			monto_objetado = body.get("montoObjetado")
			sxos = SolicitudXOportunidad(
				idSolicitud=solicitud.id,
				idOportunidad=id_oportunidad,
				montoPropuesto=monto_propuesto,
				montoObjetado=monto_objetado
			)
			db.add(sxos)
			db.commit()

			return {"msg": "Solicitud AGREGAR_ALUMNO creada", "id": solicitud.id}
		elif tipo_solicitud == "EDICION_ALUMNO":
			#  idPropuesta (obtener del programa a que propuesta esta asociado)
			# "idPrograma", (OBLIGATORIO)
			# "idOportunidad", (OBLIGATORIO)
			# "idUsuarioGenerador" (OBLIGATORIO)
			# "montoPropuesto", (OBLIGATORIO)
			# "montoObjetado", (OBLIGATORIO)
			# "tipoSolicitud_id", " (obtener el id de este "tipo_solicitud")",
			# "valorSolicitud_id" (obtener el id de  "ABIERTA")
			# "idUsuarioReceptor (obtener del idPrograma)"
			# comentario "El monto  propuesto fue editado por el usuario (obtener el nombre del usuario generador) de oporutnidad.monto, oportunidad..monto_propuesto"
			# abierta = True
			pass
		elif tipo_solicitud == "ELIMINACION_BECADO":
			#Por ahora esto no genera una solicitud
			pass
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			#  idPropuesta (obtener del programa a que propuesta esta asociado)
			# "idPrograma", (OBLIGATORIO)
			# "idUsuarioGenerador" (OBLIGATORIO)
			# "tipoSolicitud_id", " (obtener el id de este "tipo_solicitud	")",
			# "valorSolicitud_id" (obtener el id de  "ABIERTA")
			# "idUsuarioReceptor (obtener del idPrograma)"
			# comentario (OBLIGATORIO)
			# abierta = True
			pass
		elif tipo_solicitud == "FECHA_CAMBIADA":
			pass
	return



@router.get("/listar", response_model=List[Solicitud])
def listar_solicitudes(db: Session = Depends(get_db)):
	solicitudes = db.query(SolicitudModel).all()
	resultado = []
	for s in solicitudes:
		sxos = db.query(SolicitudXOportunidad).filter_by(idSolicitud=s.id).first()
		sxps = db.query(SolicitudXPrograma).filter_by(idSolicitud=s.id).first()
		oportunidad = None
		programa = None
		if sxos:
			oportunidad = SolicitudOportunidad(
				idOportunidad=sxos.idOportunidad,
				montoPropuesto=sxos.montoPropuesto,
				montoObjetado=sxos.montoObjetado
			)
		if sxps:
			programa = SolicitudPrograma(
				idPrograma=sxps.idPrograma,
				fechaInaguracionPropuesta=sxps.fechaInaguracionPropuesta,
				fechaInaguracionObjetada=sxps.fechaInaguracionObjetada
			)
		resultado.append(Solicitud(
			id=s.id,
			idUsuarioReceptor=s.idUsuarioReceptor,
			idUsuarioGenerador=s.idUsuarioGenerador,
			abierta=s.abierta,
			tipoSolicitud=s.tipoSolicitud.nombre if s.tipoSolicitud else None,
			valorSolicitud=s.valorSolicitud.nombre if s.valorSolicitud else None,
			idPropuesta=s.idPropuesta,
			comentario=s.comentario,
			creadoEn=s.creadoEn,
			oportunidad=oportunidad,
			programa=programa
		))
	return resultado

