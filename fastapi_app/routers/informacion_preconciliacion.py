
from fastapi_app.models.propuesta import Propuesta
from fastapi_app.models.programa import Programa
from fastapi_app.models.oportunidad import Oportunidad
from datetime import datetime, timedelta


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma
from fastapi_app.models.usuario import Usuario
from fastapi_app.models.cartera import Cartera

# def obtener_carteras_usuario(id_usuario: int, db: Session):
#     usuario = db.query(Usuario).get(id_usuario)
#     if not usuario:
#         return []
#     # Si el usuario tiene relación many-to-many con carteras
#     carteras = usuario.carteras if hasattr(usuario, 'carteras') else []
#     return [
#         {
#             "id": c.id,
#             "nombre": c.nombre,
#             "descripcion": getattr(c, "descripcion", None)
#         }
#         for c in carteras
#     ]


def obtener_solicitudes_aprobacion_jp(id_usuario: int, id_propuesta: int, db: Session):
    """
    Obtiene solicitudes de tipo APROBACION_JP para un usuario y propuesta.
    Retorna lista de solicitudes con su estado abierta (bool).
    """
    solicitudes = db.query(SolicitudModel).filter(
        ((SolicitudModel.idUsuarioGenerador == id_usuario) | (SolicitudModel.idUsuarioReceptor == id_usuario)),
        SolicitudModel.idPropuesta == id_propuesta
    ).all()
    
    solicitudes_aprobacion_jp = []
    for s in solicitudes:
        if s.tipoSolicitud and s.tipoSolicitud.nombre == "APROBACION_JP":
            solicitudes_aprobacion_jp.append({
                "id": s.id,
                "abierta": s.abierta,
                "valorSolicitud": s.valorSolicitud.nombre if s.valorSolicitud else None,
                "comentario": s.comentario,
                "creadoEn": s.creadoEn
            })
    
    return solicitudes_aprobacion_jp

def obtener_solicitudes_agrupadas(id_usuario: int, id_propuesta: int, db: Session):
    if id_usuario == 2: 
        id_usuario = 1
    tipos_oportunidad = {"AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"}
    tipo_programa = {"EXCLUSION_PROGRAMA","FECHA_CAMBIADA"}
    solicitudes = db.query(SolicitudModel).filter(
        ((SolicitudModel.idUsuarioGenerador == id_usuario) | (SolicitudModel.idUsuarioReceptor == id_usuario)),
        SolicitudModel.idPropuesta == id_propuesta
    ).all()
    solicitudesPropuestaOportunidad = []
    solicitudesPropuestaPrograma = []
    solicitudesGenerales = []
    for s in solicitudes:
        sxos = db.query(SolicitudXOportunidad).filter_by(idSolicitud=s.id).first()
        sxps = db.query(SolicitudXPrograma).filter_by(idSolicitud=s.id).first()
        oportunidad = None
        programa = None
        if sxos:
            oportunidad_db = db.query(Oportunidad).filter_by(id=sxos.idOportunidad).first()
            oportunidad = SolicitudOportunidad(
                idOportunidad=sxos.idOportunidad,
                montoPropuesto=sxos.montoPropuesto,
                montoObjetado=sxos.montoObjetado
            )
            if oportunidad_db:
                oportunidad_dict = oportunidad.model_dump()
                oportunidad_dict.update({
                    "nombre": oportunidad_db.nombre,
                    "monto":oportunidad_db.monto,
                    "montoPropuestoOportunidad": oportunidad_db.montoPropuesto,
                    "dni": oportunidad_db.documentoIdentidad,
                })
                oportunidad = oportunidad_dict
            # Obtener el nombre del programa asociado a la oportunidad y ponerlo en el objeto programa
            programa = None
            if oportunidad_db:
                programa_db = db.query(Programa).filter_by(id=oportunidad_db.idPrograma).first()
                if programa_db:
                    # Armar objeto con la forma de SolicitudPrograma y agregar el nombre
                    programa = {
                        "idPrograma": programa_db.id,
                        "fechaInaguracionPropuesta": None,
                        "fechaInaguracionObjetada": None,
                        "nombre": programa_db.nombre
                    }
        elif sxps:
            programa_db = db.query(Programa).filter_by(id=sxps.idPrograma).first()
            programa = SolicitudPrograma(
                idPrograma=sxps.idPrograma,
                fechaInaguracionPropuesta=sxps.fechaInaguracionPropuesta,
                fechaInaguracionObjetada=sxps.fechaInaguracionObjetada
            )
            if programa_db:
                programa_dict = programa.model_dump()
                programa_dict.update({
                    "nombre": programa_db.nombre,
                    "puntoMinimoApertura": programa_db.puntoMinimoApertura,
                })
                programa = programa_dict
            # Si es solicitud de programa, no mostrar nada en oportunidad
            oportunidad = None
        solicitud_dict = Solicitud(
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
        ).model_dump()
        tipo = solicitud_dict["tipoSolicitud"]
        if tipo in tipos_oportunidad:
            solicitudesPropuestaOportunidad.append(solicitud_dict)
        elif tipo in tipo_programa:
            solicitudesPropuestaPrograma.append(solicitud_dict)
        else:
            solicitudesGenerales.append(solicitud_dict)
    if id_usuario in [2, 4, 5, 6]:
        return {"solicitudesGenerales": solicitudesGenerales}
    else:
        return {
            "solicitudesPropuestaOportunidad": solicitudesPropuestaOportunidad,
            "solicitudesPropuestaPrograma": solicitudesPropuestaPrograma,
        }


def obtener_programas_mes_conciliado(id_usuario: int, id_propuesta: int, db: Session, solicitudes):
    propuesta = db.query(Propuesta).get(id_propuesta)
    if not propuesta or not propuesta.fechaPropuesta:
        return {"items": [], "totalizadores": {}}
    mes_conciliacion = propuesta.fechaPropuesta
    if mes_conciliacion.month == 1:
        mes_anterior = 12
        anio_anterior = mes_conciliacion.year - 1
    else:
        mes_anterior = mes_conciliacion.month - 1
        anio_anterior = mes_conciliacion.year
    ids_no_filtrar = {1,2,3,4,5,6}
    if id_usuario in ids_no_filtrar:
        programas = db.query(Programa).filter(
            Programa.idPropuesta == id_propuesta
        ).all()
    else:
        programas = db.query(Programa).filter(
            Programa.idJefeProducto == id_usuario,
            Programa.idPropuesta == id_propuesta
        ).all()
    programas_filtrados = [p for p in programas if p.fechaInaguracionPropuesta.month == mes_anterior and p.fechaInaguracionPropuesta.year == anio_anterior]
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"]
    oportunidades_all = db.query(Oportunidad).filter(Oportunidad.idPropuesta == id_propuesta, Oportunidad.etapaVentaPropuesta.notin_(etapas_excluir)).all()
    oportunidades_por_programa = {}
    for o in oportunidades_all:
        oportunidades_por_programa.setdefault(o.idPrograma, []).append(o)
    items = []
    total_meta = 0
    total_monto = 0
    total_oportunidades = 0
    # Obtener ids de alumnos y programas involucrados en solicitudes ACEPTADAS
    alumnos_solicitudes = set()
    programas_solicitudes = set()
    programas_fecha_editada = set()  # Programas con solicitud FECHA_CAMBIADA
    for s in solicitudes.get("solicitudesPropuestaOportunidad", []):
        # No considerar solicitudes ACEPTADAS
        if s.get("valorSolicitud") == "ACEPTADO":
            continue
        oportunidad = s.get("oportunidad")
        if oportunidad and oportunidad.get("idOportunidad"):
            alumnos_solicitudes.add(oportunidad["idOportunidad"])
    for s in solicitudes.get("solicitudesPropuestaPrograma", []):
        # No considerar solicitudes ACEPTADAS
        if s.get("valorSolicitud") == "ACEPTADO":
            continue
        programa = s.get("programa")
        if programa and programa.get("idPrograma"):
            programas_solicitudes.add(programa["idPrograma"])
            # Si es solicitud de tipo FECHA_CAMBIADA, agregarlo al set
            if s.get("tipoSolicitud") == "FECHA_CAMBIADA":
                programas_fecha_editada.add(programa["idPrograma"])
    for p in programas_filtrados:
        # Excluir programas con noAperturar = True
        if p.noAperturar:
            continue
            
        oportunidades = oportunidades_por_programa.get(p.id, [])
        monto_opty = sum(o.montoPropuesto or 0 for o in oportunidades)
        count_opty = len(oportunidades)
        # Verificar si el programa es atípico
        atipico = False
        # Si el programa está en alguna solicitud de programa
        if p.id in programas_solicitudes:
            atipico = True
        # Si alguna oportunidad/alumno del programa está en alguna solicitud de oportunidad
        else:
            for o in oportunidades:
                if o.id in alumnos_solicitudes:
                    atipico = True
                    break
        items.append({
            "id": p.id,
            "nombre": p.nombre,
            "fechaDeInaguracion": p.fechaInaguracionPropuesta,
            "codigo": p.codigo,
            "moneda": p.moneda,
            "precioDeLista": p.precioDeLista,
            "metaDeVenta": p.metaDeVenta,
            "puntoMinimoApertura": p.puntoMinimoApertura,
            "subdireccion": p.subdireccion,
            "cartera": p.cartera,
            "oportunidad_total_monto_propuesto": monto_opty,
            "metaDeAlumnos": p.metaDeAlumnos,
            "oportunidad_total_count": count_opty,
            "atipico": bool(atipico),
            "enRiesgo": bool(count_opty < p.puntoMinimoApertura),
            "noAperturar": bool(p.noAperturar),
            "comentario": p.comentario,
            "fechaEditada": bool(p.id in programas_fecha_editada)

        })
        total_meta += p.metaDeVenta or 0
        total_monto += monto_opty   
        total_oportunidades += count_opty
    totalizadores = {
        "total_meta_de_venta": total_meta,
        "total_monto_propuesto": total_monto,
        "total_oportunidades": total_oportunidades,
        "size": len(items)
    }
    return {"items": items, "totalizadores": totalizadores}
def obtener_programas_meses_anteriores(id_usuario: int, id_propuesta: int, db: Session, solicitudes):
    propuesta = db.query(Propuesta).get(id_propuesta)
    if not propuesta or not propuesta.fechaPropuesta:
        return {"items": [], "totalizadores": {}}
    mes_conciliacion = propuesta.fechaPropuesta
    items = []
    total_meta = 0
    total_monto = 0
    total_oportunidades = 0
    ids_no_filtrar = {1,2,3,4,5,6}
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"]
    oportunidades_all = db.query(Oportunidad).filter(Oportunidad.idPropuesta == id_propuesta, Oportunidad.etapaVentaPropuesta.notin_(etapas_excluir)).all()
    oportunidades_por_programa = {}
    for o in oportunidades_all:
        oportunidades_por_programa.setdefault(o.idPrograma, []).append(o)

    # Obtener ids de alumnos y programas involucrados en solicitudes ACEPTADAS
    alumnos_solicitudes = set()
    programas_solicitudes = set()
    programas_fecha_editada = set()  # Programas con solicitud FECHA_CAMBIADA
    for s in solicitudes.get("solicitudesPropuestaOportunidad", []):
        # No considerar solicitudes ACEPTADAS
        if s.get("valorSolicitud") == "ACEPTADO":
            continue
        oportunidad = s.get("oportunidad")
        if oportunidad and oportunidad.get("idOportunidad"):
            alumnos_solicitudes.add(oportunidad["idOportunidad"])
    for s in solicitudes.get("solicitudesPropuestaPrograma", []):
        # NO considerar solicitudes ACEPTADAS
        if s.get("valorSolicitud") == "ACEPTADO":
            continue
        programa = s.get("programa")
        if programa and programa.get("idPrograma"):
            programas_solicitudes.add(programa["idPrograma"])
            # Si es solicitud de tipo FECHA_CAMBIADA, agregarlo al set
            if s.get("tipoSolicitud") == "FECHA_CAMBIADA":
                programas_fecha_editada.add(programa["idPrograma"])

    for offset in [2, 3, 4]:
        mes = mes_conciliacion.month - offset
        anio = mes_conciliacion.year
        while mes <= 0:
            mes += 12
            anio -= 1
        if id_usuario in ids_no_filtrar:
            programas = db.query(Programa).filter(
                Programa.idPropuesta == id_propuesta
            ).all()
        else:
            programas = db.query(Programa).filter(
                Programa.idJefeProducto == id_usuario,
                Programa.idPropuesta == id_propuesta
            ).all()
        programas_filtrados = [p for p in programas if p.fechaInaguracionPropuesta.month == mes and p.fechaInaguracionPropuesta.year == anio]
        for p in programas_filtrados:
            # Excluir programas con noAperturar = True
            if p.noAperturar:
                continue
                
            oportunidades = oportunidades_por_programa.get(p.id, [])
            monto_opty = sum(o.montoPropuesto or 0 for o in oportunidades)
            count_opty = len(oportunidades)
            # Verificar si el programa es atípico
            atipico = False
            if p.id in programas_solicitudes:
                atipico = True
            else:
                for o in oportunidades:
                    if o.id in alumnos_solicitudes:
                        atipico = True
                        break
            items.append({
                "id": p.id,
                "nombre": p.nombre,
                "fechaDeInaguracion": p.fechaInaguracionPropuesta,
                "codigo": p.codigo,
                "moneda": p.moneda,
                "precioDeLista": p.precioDeLista,
                "metaDeVenta": p.metaDeVenta,
                "metaDeAlumnos": p.metaDeAlumnos,
                "puntoMinimoApertura": p.puntoMinimoApertura,
                "subdireccion": p.subdireccion,
                "cartera": p.cartera,
                "mes": p.mesPropuesto,
                "oportunidad_total_monto_propuesto": monto_opty,
                "oportunidad_total_count": count_opty,
                "atipico": atipico,
                "enRiesgo": bool(count_opty < p.puntoMinimoApertura),
                "comentario": p.comentario,
                "fechaEditada": bool(p.id in programas_fecha_editada)
            })
            total_meta += p.metaDeVenta or 0
            total_monto += monto_opty
            total_oportunidades += count_opty
    totalizadores = {
        "total_meta_de_venta": total_meta,
        "total_monto_propuesto": total_monto,
        "total_oportunidades": total_oportunidades,
        "size": len(items)
    }
    return {"items": items, "totalizadores": totalizadores}

router = APIRouter(prefix="/informacion-preconciliacion", tags=["InformacionPreconciliacion"])
@router.get("/listar")
def obtener_informacion_preconciliacion(
    id_usuario: int = Query(..., description="ID del usuario (generador o receptor)"),
    id_propuesta: int = Query(..., description="ID de la propuesta"),
    db: Session = Depends(get_db)
):
    solicitudes = obtener_solicitudes_agrupadas(id_usuario, id_propuesta, db)
    # carteras = obtener_carteras_usuario(id_usuario, db)
    programas_mes_conciliado = obtener_programas_mes_conciliado(id_usuario, id_propuesta, db, solicitudes)
    programas_meses_anteriores = obtener_programas_meses_anteriores(id_usuario, id_propuesta, db, solicitudes)

    # Obtener la propuesta y su estado
    propuesta = db.query(Propuesta).get(id_propuesta)
    estado_generada = False
    estado_propuesta_nombre = ""
    if propuesta and propuesta.estadoPropuesta and propuesta.estadoPropuesta.nombre:
        estado_propuesta_nombre = propuesta.estadoPropuesta.nombre.strip().upper()
        estado_generada = estado_propuesta_nombre == "GENERADA"
        estado_preconciliada = estado_propuesta_nombre == "PRECONCILIADA"

    # Obtener rol del usuario (cada usuario tiene máximo un rol)
    usuario = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    rol_usuario = None
    if usuario and usuario.roles:
        rol_usuario = usuario.roles[0].nombre if len(usuario.roles) > 0 else None
    
    response = {
        # "carteras": carteras,
        "mes_conciliado": programas_mes_conciliado,
        "meses_anteriores": programas_meses_anteriores,
    }
    if not estado_generada:
        response["solicitudes"] = solicitudes  
    # verBotonPreconciliacion: Solo DAF Supervisor o DAF Subdirector cuando estado == GENERADA
    if rol_usuario in ["DAF - Supervisor", "DAF - Subdirector"] and estado_generada:
        response["verBotonPreconciliacion"] = True
    
    # verBotonAprobacionSubComercial: Solo Jefes de Producto
    if rol_usuario == "Comercial - Jefe de producto":
        response["verBotonAprobacionSubComercial"] = True
        
        # verBotonAprobacionFinalizar: JP con todas sus solicitudes ACEPTADAS (o sin solicitudes)
        solicitudes_jp = solicitudes.get("solicitudesPropuestaOportunidad", []) + solicitudes.get("solicitudesPropuestaPrograma", [])
        if not solicitudes_jp or all(s.get("valorSolicitud") == "ACEPTADO" for s in solicitudes_jp):
            response["verBotonAprobacionFinalizar"] = True
        
        # verBotonAprobacionBloqueadoSubComercial: Si existe una solicitud APROBACION_JP cerrada (abierta=False)
        solicitudes_aprobacion = obtener_solicitudes_aprobacion_jp(id_usuario, id_propuesta, db)
        if any(not s["abierta"] for s in solicitudes_aprobacion):
            response["verBotonAprobacionBloqueadoSubComercial"] = True
    if (rol_usuario == "DAF - Supervisor" or rol_usuario == "DAF - Subdirector") and estado_preconciliada:
        response["noEditarBotonSolicitarCambio"] = True
        
    return response
