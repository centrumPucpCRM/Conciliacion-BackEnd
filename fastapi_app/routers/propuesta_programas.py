from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.propuesta_programa import PropuestaPrograma
from ..models.programa import Programa
from ..models.propuesta_oportunidad import PropuestaOportunidad
from ..models.oportunidad import Oportunidad
from ..database import get_db
from datetime import date
from dateutil.relativedelta import relativedelta

router = APIRouter()

@router.get('/propuestas/{propuesta_id}/programas', response_model=list)
def get_programas_de_propuesta(propuesta_id: int, db: Session = Depends(get_db)):
    propuesta_programas = db.query(PropuestaPrograma).filter(
        PropuestaPrograma.id_propuesta == propuesta_id
    ).all()
    if not propuesta_programas:
        raise HTTPException(status_code=404, detail="No se encontraron programas para la propuesta")

    # Calcular los meses válidos (mes actual -1, -2, -3, -4)
    hoy = date.today()
    meses_validos = set()
    for n in [1,2,3,4]:
        mes = (hoy - relativedelta(months=n)).strftime('%Y-%m')
        meses_validos.add(mes)

    # Recopilamos primero todos los programas filtrados que cumplen con los requisitos
    programas_filtrados = []
    for pp in propuesta_programas:
        programa = db.query(Programa).filter(Programa.id_programa == pp.id_programa).first()
        if not programa:
            continue
        # Filtrar por mes de fecha_de_inauguracion
        if programa.fecha_de_inauguracion:
            mes_programa = programa.fecha_de_inauguracion.strftime('%Y-%m')
            if mes_programa not in meses_validos:
                continue
        else:
            continue
        programas_filtrados.append((programa, pp))
    
    # Ordenamos los programas primero por cartera y luego por fecha de inauguración (descendente)
    # Para ordenar fechas en orden descendente, usamos el negativo del número de días desde una fecha de referencia
    from datetime import date as date_type
    epoch = date_type(1970, 1, 1)
    
    def fecha_comparacion(programa):
        if programa[0].fecha_de_inauguracion:
            # Para ordenar de forma descendente, usamos el negativo
            return -((programa[0].fecha_de_inauguracion - epoch).days)
        return 0  # Si no hay fecha, va al final
        
    programas_filtrados.sort(key=lambda x: (x[0].cartera, fecha_comparacion(x)))
    
    # Construimos la respuesta final con los programas ordenados
    programas = []
    for programa, pp in programas_filtrados:
        # Buscar oportunidades asociadas a este propuesta_programa
        oportunidades = db.query(PropuestaOportunidad).filter(
            PropuestaOportunidad.id_propuesta_programa == pp.id_propuesta_programa
        ).all()
        oportunidades_list = []
        for o in oportunidades:
            oportunidad_real = db.query(Oportunidad).filter(Oportunidad.id_oportunidad == o.id_oportunidad).first()
            oportunidades_list.append({
                "id_propuesta_oportunidad": o.id_propuesta_oportunidad,
                "id_oportunidad": o.id_oportunidad,
                "monto_propuesto": float(o.monto_propuesto) if o.monto_propuesto is not None else None,
                "etapa_venta_propuesto": o.etapa_venta_propuesto,
                "dni": oportunidad_real.documento_identidad if oportunidad_real else None,
                "alumno": oportunidad_real.nombre if oportunidad_real else None,
                "descuento": oportunidad_real.descuento if oportunidad_real else None,
                "monto": float(oportunidad_real.monto) if oportunidad_real and oportunidad_real.monto is not None else None,
                "moneda": oportunidad_real.moneda if oportunidad_real else None,
                "fecha_matricula": oportunidad_real.fecha_matricula.isoformat() if oportunidad_real and oportunidad_real.fecha_matricula else None,
                # Añadimos los campos adicionales
                "posible_atipico": oportunidad_real.posible_atipico if oportunidad_real else None,
                "becado": oportunidad_real.becado if oportunidad_real else None,
                "conciliado": oportunidad_real.conciliado if oportunidad_real else None
            })
        programas.append({
            "id": programa.id_programa,  # Añadimos este campo para consistencia con el frontend
            "id_programa": programa.id_programa,
            "codigo": programa.codigo,
            "nombre": programa.nombre,
            "fecha_de_inicio": programa.fecha_de_inicio,
            "fecha_de_inauguracion": programa.fecha_de_inauguracion,
            "fecha_ultima_postulante": programa.fecha_ultima_postulante,
            "moneda": programa.moneda,
            "meta_venta": programa.meta_venta,
            "meta_alumnos": programa.meta_alumnos,
            "punto_minimo_apertura": programa.punto_minimo_apertura,
            "cartera": programa.cartera,
            "precio_lista": programa.precio_lista,
            "id_jefe_producto": programa.id_jefe_producto,
            "id_propuesta_programa": pp.id_propuesta_programa,
            "oportunidades": oportunidades_list
        })
    return programas
