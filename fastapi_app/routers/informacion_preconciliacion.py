
from fastapi_app.models.propuesta import Propuesta
from fastapi_app.models.programa import Programa
from datetime import datetime, timedelta


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import SolicitudOut, SolicitudOportunidad, SolicitudPrograma
from fastapi_app.models.usuario import Usuario
from fastapi_app.models.cartera import Cartera

def obtener_carteras_usuario(id_usuario: int, db: Session):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        return []
    # Si el usuario tiene relación many-to-many con carteras
    carteras = usuario.carteras if hasattr(usuario, 'carteras') else []
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "descripcion": getattr(c, "descripcion", None)
        }
        for c in carteras
    ]
def obtener_solicitudes_agrupadas(id_usuario: int, id_propuesta: int, db: Session):
    if id_usuario == 1:
        id_usuario = 2
    tipos_oportunidad = {"AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"}
    tipo_programa = "EXCLUSION_PROGRAMA"
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
        solicitud_dict = SolicitudOut(
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
        ).dict()
        tipo = solicitud_dict["tipoSolicitud"]
        if tipo in tipos_oportunidad:
            solicitudesPropuestaOportunidad.append(solicitud_dict)
        elif tipo == tipo_programa:
            solicitudesPropuestaPrograma.append(solicitud_dict)
        else:
            solicitudesGenerales.append(solicitud_dict)
    return {
        "solicitudesPropuestaOportunidad": solicitudesPropuestaOportunidad,
        "solicitudesPropuestaPrograma": solicitudesPropuestaPrograma,
        "solicitudesGenerales": solicitudesGenerales
    }


def obtener_programas_mes_conciliado(id_usuario: int, id_propuesta: int, db: Session):
    propuesta = db.query(Propuesta).get(id_propuesta)
    if not propuesta or not propuesta.fechaPropuesta:
        return []
    # Obtener mes de conciliacion y calcular mes anterior
    mes_conciliacion = propuesta.fechaPropuesta
    # Calcular mes y año del mes anterior
    if mes_conciliacion.month == 1:
        mes_anterior = 12
        anio_anterior = mes_conciliacion.year - 1
    else:
        mes_anterior = mes_conciliacion.month - 1
        anio_anterior = mes_conciliacion.year
    ids_no_filtrar = {1,2,3,4,5,6}# Usuarios: daf,admin,jefes comerciales
    if id_usuario in ids_no_filtrar:
        programas = db.query(Programa).filter(
            Programa.fechaDeInaguracion != None
        ).all()
    else:
        programas = db.query(Programa).filter(
            Programa.idJefeProducto == id_usuario,
            Programa.fechaDeInaguracion != None
        ).all()
    programas_filtrados = [
        p for p in programas
        if p.fechaDeInaguracion.month == mes_anterior and p.fechaDeInaguracion.year == anio_anterior
    ]
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "fechaDeInaguracion": p.fechaDeInaguracion,
            "codigo": p.codigo,
            "moneda": p.moneda,
            "precioDeLista": p.precioDeLista,
            "metaDeVenta": p.metaDeVenta,
            "puntoMinimoApertura": p.puntoMinimoApertura,
            "subdireccion": p.subdireccion
        }
        for p in programas_filtrados
    ]
def obtener_programas_meses_anteriores(id_usuario: int, id_propuesta: int, db: Session):
    propuesta = db.query(Propuesta).get(id_propuesta)
    if not propuesta or not propuesta.fechaPropuesta:
        return {}
    mes_conciliacion = propuesta.fechaPropuesta
    programas_meses = []
    ids_no_filtrar = {1,2,3,4,5,6}
    for offset in [2, 3, 4]:
        mes = mes_conciliacion.month - offset
        anio = mes_conciliacion.year
        while mes <= 0:
            mes += 12
            anio -= 1
        if id_usuario in ids_no_filtrar:
            programas = db.query(Programa).filter(
                Programa.fechaDeInaguracion != None
            ).all()
        else:
            programas = db.query(Programa).filter(
                Programa.idJefeProducto == id_usuario,
                Programa.fechaDeInaguracion != None
            ).all()
        programas_filtrados = [
            p for p in programas
            if p.fechaDeInaguracion.month == mes and p.fechaDeInaguracion.year == anio
        ]
        for p in programas_filtrados:
            programas_meses.append({
                "id": p.id,
                "nombre": p.nombre,
                "fechaDeInaguracion": p.fechaDeInaguracion,
                "codigo": p.codigo,
                "moneda": p.moneda,
                "precioDeLista": p.precioDeLista,
                "metaDeVenta": p.metaDeVenta,
                "puntoMinimoApertura": p.puntoMinimoApertura,
                "subdireccion": p.subdireccion
            })
    return programas_meses
router = APIRouter(prefix="/informacion-preconciliacion", tags=["InformacionPreconciliacion"])
@router.get("/listar")
def obtener_informacion_preconciliacion(
    id_usuario: int = Query(..., description="ID del usuario (generador o receptor)"),
    id_propuesta: int = Query(..., description="ID de la propuesta"),
    db: Session = Depends(get_db)
):
    solicitudes = obtener_solicitudes_agrupadas(id_usuario, id_propuesta, db)
    carteras = obtener_carteras_usuario(id_usuario, db)
    programas_mes_conciliado = obtener_programas_mes_conciliado(id_usuario, id_propuesta, db)
    programas_meses_anteriores = obtener_programas_meses_anteriores(id_usuario, id_propuesta, db)
    return {
        "carteras": carteras,
        "solicitudes": solicitudes,
        "mes_conciliado": programas_mes_conciliado,
        "meses_anteriores": programas_meses_anteriores
    }
