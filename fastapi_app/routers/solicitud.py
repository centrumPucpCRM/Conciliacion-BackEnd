
from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.oportunidad import Oportunidad

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma

from fastapi import Body

from sqlalchemy.orm import Session
from typing import List

from ..utils.solicitudes_crear import crear_solicitud_alumno, crear_solicitud_programa
from ..utils.solicitudes_editar import aceptar_rechazar_solicitud_basico,aceptar_rechazar_edicion_alumno

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
		elif tipo_solicitud == "ELIMINACION_BECADO":
			oportunidad.eliminado = True
			oportunidad.montoPropuesto = 0
			db.commit()
			return {"msg": "Oportunidad marcada como eliminada", "idOportunidad": id_oportunidad}
		elif tipo_solicitud == "ELIMINACION_BECADO_REVERTIR":
			oportunidad.eliminado = False
			oportunidad.montoPropuesto = oportunidad.monto
			db.commit()
			return {"msg": "Oportunidad revertida a no eliminada", "idOportunidad": id_oportunidad}
		
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return crear_solicitud_programa(body, db)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			#To do: Implementar cambio de fecha en programa
			pass
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
	print(body)
	idSolicitud = body.get("idSolicitud")
	print(idSolicitud)
	solicitud = db.query(SolicitudModel).filter_by(id=idSolicitud).first()
	print(solicitud)
	print(solicitud.tipoSolicitud)
	print(solicitud.tipoSolicitud.nombre)
	tipo_solicitud = solicitud.tipoSolicitud.nombre

	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO","ELIMINACION_BECADO_REVERTIR"]:
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return aceptar_rechazar_solicitud_basico(body, db,solicitud)
		elif tipo_solicitud == "EDICION_ALUMNO":
			pass
			return aceptar_rechazar_edicion_alumno(body, db,solicitud)
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return aceptar_rechazar_solicitud_basico(body, db,solicitud)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			pass
	return

@router.post("/crearLote")
def crear_solicitudes_lote(
	body: dict = Body(...),
	db: Session = Depends(get_db)
):
	resultados = {"alumnos_aniadido": [], "alumnos_edicion": [], "programas_eliminar": [], "becas_eliminadas": [], "errores": []}
	# Procesar alumnos añadidos
	alumnos_aniadido = body.get("alumnos_aniadido", [])
	print(f"Procesando alumnos_aniadido: {alumnos_aniadido}")
	for idx, solicitud in enumerate(alumnos_aniadido):
		print(f"Procesando alumnos_aniadido[{idx}]: {solicitud}")
		try:
			res = crear_solicitud_alumno(solicitud, db)
			print(f"Resultado crear_solicitud_alumno: {res}")
			resultados["alumnos_aniadido"].append(res)
		except Exception as e:
			print(f"Error en alumnos_aniadido[{idx}]: {e}")
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar alumnos edición
	alumnos_edicion = body.get("alumnos_edicion", [])
	print(f"Procesando alumnos_edicion: {alumnos_edicion}")
	for idx, solicitud in enumerate(alumnos_edicion):
		print(f"Procesando alumnos_edicion[{idx}]: {solicitud}")
		try:
			res = crear_solicitud_alumno(solicitud, db)
			print(f"Resultado crear_solicitud_alumno: {res}")
			resultados["alumnos_edicion"].append(res)
		except Exception as e:
			print(f"Error en alumnos_edicion[{idx}]: {e}")
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar programas eliminar
	programas_eliminar = body.get("programas_eliminar", [])
	print(f"Procesando programas_eliminar: {programas_eliminar}")
	for idx, solicitud in enumerate(programas_eliminar):
		print(f"Procesando programas_eliminar[{idx}]: {solicitud}")
		try:
			res = crear_solicitud_programa(solicitud, db)
			print(f"Resultado crear_solicitud_programa: {res}")
			resultados["programas_eliminar"].append(res)
		except Exception as e:
			print(f"Error en programas_eliminar[{idx}]: {e}")
			resultados["errores"].append({"solicitud": solicitud, "error": str(e)})
	# Procesar becas eliminadas
	becas_eliminadas = body.get("becas_eliminadas", [])
	print(f"Procesando becas_eliminadas: {becas_eliminadas}")
	for idx, item in enumerate(becas_eliminadas):
		print(f"Procesando becas_eliminadas[{idx}]: {item}")
		try:
			id_oportunidad = item.get("idOportunidad")
			if not id_oportunidad:
				raise ValueError("Falta campo obligatorio: idOportunidad")
			
			oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
			if not oportunidad:
				raise ValueError(f"Oportunidad {id_oportunidad} no encontrada")
			
			oportunidad.eliminado = True
			oportunidad.montoPropuesto = 0
			db.commit()
			
			resultados["becas_eliminadas"].append({
				"msg": "Oportunidad marcada como eliminada",
				"idOportunidad": id_oportunidad
			})
			print(f"Oportunidad {id_oportunidad} marcada como eliminada")
		except Exception as e:
			print(f"Error en becas_eliminadas[{idx}]: {e}")
			resultados["errores"].append({"item": item, "error": str(e)})
	print(f"Resultados finales: {resultados}")
	return resultados

