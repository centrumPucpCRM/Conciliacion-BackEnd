
from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel, ValorSolicitud
from fastapi_app.models.oportunidad import Oportunidad

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma

from fastapi import Body

from sqlalchemy.orm import Session
from typing import List

from ..utils.solicitudes_crear import crear_solicitud_alumno, crear_solicitud_programa, crear_solicitud_fecha, crear_solicitud_ELIMINACION_POSIBLE_BECADO
from ..utils.solicitudes_editar import aceptar_rechazar_solicitud_basico,aceptar_rechazar_edicion_alumno, aceptar_rechazar_fecha_cambiada, aceptar_rechazar_ELIMINACION_POSIBLE_BECADO
from ..utils.solicitudes_flujo import aceptar_rechazar_solicitud_subdirectores

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])
# Endpoint generico para crear solicitudes de alumno o programa
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

@router.post("/crear")
def crear_solicitud_generica(
	body: dict = Body(
		...,
		example={
			"AGREGAR_ALUMNO":{
				"idUsuario": 2, #El id del usuario que hace la solicitud
				"tipo_solicitud": "AGREGAR_ALUMNO",
				"idOportunidad": 10,
				"comentario": "Agregar de alumno por solicitud del usuario."
			},
			"EDICION_ALUMNO":{
				"tipo_solicitud": "EDICION_ALUMNO",
				"idOportunidad": 10,
				"montoPropuesto": 1000,
			},
			"EXCLUSION_PROGRAMA":{
				"tipo_solicitud": "EXCLUSION_PROGRAMA",
				"idPrograma": 218,
				"comentario": "DAF solicita la exclusión del programa."
			}
		}
	),
	db: Session = Depends(get_db)
):
	tipo_solicitud = body.get("tipo_solicitud")
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO","ELIMINACION_BECADO_REVERTIR"]:
		id_oportunidad = body.get("idOportunidad")
		oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return crear_solicitud_alumno(body, db)
		elif tipo_solicitud == "EDICION_ALUMNO":
			return crear_solicitud_alumno(body, db)
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return crear_solicitud_programa(body, db)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			return crear_solicitud_fecha(body, db)
	return

@router.patch("/editar")
def editar_solicitud_generica(
	body: dict = Body(
		...,
		example={
			#Aca lo que se puede hacer es o aceptar o rechazar la solicitud
			#El usuario tiene que enviar un comentario
			#Ejemplo de aceptar
			"AGREGAR_ALUMNO":{
				"idSolicitud": 5,#tipo_solicitud:"AGREGAR_ALUMNO",
				"valorSolicitud": "ACEPTADO",
			},
			#Ejemplo de rechazar
			"AGREGAR_ALUMNO":{
				"idSolicitud": 5,#tipo_solicitud:"AGREGAR_ALUMNO",
				"valorSolicitud": "RECHAZADO",
				"comentario": "Agregar de alumno por solicitud del usuario."
			},

			#Aca lo que se puede hacer es o aceptar o rechazar la solicitud
			#El usuario tiene que enviar un comentario		
			#Ejemplo de rechazar	
			"EXCLUSION_PROGRAMA":{
				"idSolicitud": 5,#tipo_solicitud:"EXCLUSION_PROGRAMA",
				"valorSolicitud": "ACEPTADO",
			},
			#Ejemplo de rechazar	
			"EXCLUSION_PROGRAMA":{
				"idSolicitud": 5,#tipo_solicitud:"EXCLUSION_PROGRAMA",
				"valorSolicitud": "RECHAZADO",
				"comentario": "DAF solicita la exclusión del programa."
			},
			#Si el montoObjetado tiene valor, el valor de este pasa a montoPropuesto(anterior)
			#Y el montoObjetado es el nuevo valor
			#Se genera un comentario automaticamente
			"EDICION_ALUMNO":{
				"tipo_solicitud": "EDICION_ALUMNO",
				"idOportunidad": 10,
				"montoObjetado": 500,
			},

		}
	),
	db: Session = Depends(get_db)
):
	idSolicitud = body.get("idSolicitud")
	solicitud = db.query(SolicitudModel).filter_by(id=idSolicitud).first()
	tipo_solicitud = solicitud.tipoSolicitud.nombre
	print(body)
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO"]:
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return aceptar_rechazar_solicitud_basico(body, db,solicitud)
		elif tipo_solicitud == "EDICION_ALUMNO":
			return aceptar_rechazar_edicion_alumno(body, db,solicitud)
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return aceptar_rechazar_solicitud_basico(body, db,solicitud)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			return aceptar_rechazar_fecha_cambiada(body, db,solicitud)
	elif tipo_solicitud == "ELIMINACION_POSIBLE_BECADO":
		return aceptar_rechazar_ELIMINACION_POSIBLE_BECADO(body, db, solicitud)
	return

@router.post("/crearLote")
def crear_solicitudes_lote(
	body: dict = Body(...),
	db: Session = Depends(get_db)
):
	print(body)
	resultados = {"alumnos_aniadido": [], "alumnos_edicion": [], "programas_eliminar": [], "becas_eliminadas": [], "errores": []}
	# Procesar alumnos añadidos
	alumnos_aniadido = body.get("alumnos_aniadido", [])
	for idx, solicitud in enumerate(alumnos_aniadido):
		try:
			res = crear_solicitud_alumno(solicitud, db)
			resultados["alumnos_aniadido"].append(res)
		except Exception as e:
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar alumnos edición
	alumnos_edicion = body.get("alumnos_edicion", [])
	for idx, solicitud in enumerate(alumnos_edicion):
		try:
			res = crear_solicitud_alumno(solicitud, db)
			resultados["alumnos_edicion"].append(res)
		except Exception as e:
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar programas eliminar
	programas_eliminar = body.get("programas_eliminar", [])
	for idx, solicitud in enumerate(programas_eliminar):
		try:
			res = crear_solicitud_programa(solicitud, db)
			resultados["programas_eliminar"].append(res)
		except Exception as e:
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar becas eliminadas
	becas_eliminadas = body.get("becas_eliminadas", [])
	for idx, item in enumerate(becas_eliminadas):
		try:
			tipo_solicitud = item.get("tipo_solicitud")
			id_oportunidad = item.get("idOportunidad")
			
			if not id_oportunidad:
				raise ValueError("Falta campo obligatorio: idOportunidad")
			
			oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
			if not oportunidad:
				raise ValueError(f"Oportunidad {id_oportunidad} no encontrada")
			
			# Si el tipo es ELIMINACION_POSIBLE_BECADO, crear solicitud formal
			if tipo_solicitud == "ELIMINACION_POSIBLE_BECADO":
				res = crear_solicitud_ELIMINACION_POSIBLE_BECADO(item, db)
				resultados["becas_eliminadas"].append(res)
			# Si es ELIMINACION_BECADO (sin solicitud), marcar como eliminado directamente
			else:
				oportunidad.eliminado = True
				db.commit()
				resultados["becas_eliminadas"].append({
					"msg": "Oportunidad marcada como eliminada",
					"idOportunidad": id_oportunidad
				})
		except Exception as e:
			print(f"Error en becas_eliminadas[{idx}]: {e}")
			resultados["errores"].append({"item": item, "error": str(e)})
	return resultados


@router.patch("/abrir-solicitudes-aprobacion-jp")
def abrir_solicitudes_aprobacion_jp(
	body: dict = Body(
		...,
		example={
			"idUsuario": 7,
			"idPropuesta": 1
		}
	),
	db: Session = Depends(get_db)
):
	"""
	Abre todas las solicitudes de tipo APROBACION_JP para un usuario y propuesta.
	Pone abierta=True en todas las solicitudes APROBACION_JP del usuario.
	"""
	id_usuario = body.get("idUsuario")
	id_propuesta = body.get("idPropuesta")
	
	if not id_usuario or not id_propuesta:
		return {"error": "Se requieren idUsuario e idPropuesta"}
	
	# Buscar todas las solicitudes APROBACION_JP del usuario para la propuesta
	solicitudes = db.query(SolicitudModel).filter(
		SolicitudModel.idUsuarioGenerador == id_usuario,
		SolicitudModel.idPropuesta == id_propuesta
	).all()
	
	solicitudes_actualizadas = []
	for solicitud in solicitudes:
		if solicitud.tipoSolicitud and solicitud.tipoSolicitud.nombre == "APROBACION_JP":
			# Si el generador y receptor son el mismo, aprobar automáticamente
			if solicitud.idUsuarioGenerador == solicitud.idUsuarioReceptor:
				valor_aceptado = db.query(ValorSolicitud).filter_by(nombre="ACEPTADO").first()
				if valor_aceptado:
					solicitud.valorSolicitud_id = valor_aceptado.id
			solicitud.abierta = False
			solicitudes_actualizadas.append(solicitud.id)
	
	db.commit()
	
	return {
		"msg": f"Se abrieron {len(solicitudes_actualizadas)} solicitudes de tipo APROBACION_JP",
		"solicitudesAbiertas": solicitudes_actualizadas,
		"idUsuario": id_usuario,
		"idPropuesta": id_propuesta
	}

@router.patch("/solicitudesSubdirectores")
def editar_solicitud_subdirectores(
	body: dict = Body(
		...,
		example={
			"ACEPTADO": {
				"idSolicitud": 10,
				"valorSolicitud": "ACEPTADO",
				"comentario": "Solicitud aprobada por subdirector"
			},
			"RECHAZADO": {
				"idSolicitud": 10,
				"valorSolicitud": "RECHAZADO",
				"comentario": "Solicitud rechazada, requiere revisión"
			}
		}
	),
	db: Session = Depends(get_db)
):
	"""
	Endpoint para que subdirectores acepten o rechacen solicitudes de tipo APROBACION_JP y APROBACION_COMERCIAL.
	
	- Si es RECHAZADO: cambia 'abierta' a True (para que vuelva a aparecer en la lista)
	- Si es ACEPTADO: cambia 'valorSolicitud' a ACEPTADO
	"""
	idSolicitud = body.get("idSolicitud")
	
	if not idSolicitud:
		return {"error": "Se requiere idSolicitud"}
	
	solicitud = db.query(SolicitudModel).filter_by(id=idSolicitud).first()
	
	if not solicitud:
		return {"error": "Solicitud no encontrada"}
	
	tipo_solicitud = solicitud.tipoSolicitud.nombre if solicitud.tipoSolicitud else None
	
	# Validar que sea una solicitud de subdirector
	if tipo_solicitud not in ["APROBACION_JP", "APROBACION_COMERCIAL"]:
		return {"error": "Este endpoint solo maneja solicitudes de tipo APROBACION_JP y APROBACION_COMERCIAL"}
	
	return aceptar_rechazar_solicitud_subdirectores(body, db, solicitud)