from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.cartera import Cartera as CarteraModel
from ..models.usuario import Usuario as UsuarioModel

import requests
import xml.etree.ElementTree as ET
import re


router = APIRouter(prefix="/cartera", tags=["Cartera"])


def read_session_id_from_s3():
    url = "https://cloudpot.s3.us-east-1.amazonaws.com/LogOn.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        return content
    except Exception as e:
        print(f"Error al leer desde el link: {e}")
        return None

def obtener_cartera_year():
    REPORT_PATH = '/shared/Custom/Reportes CENTRUM/Marketing/Dashboard Ventas/Andre/Soap Conciliacion/Operativo - Productos'
    session_id = str(read_session_id_from_s3())
    NAMESPACES = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'saw': 'urn://oracle.bi.webservices/v6'
    }
    SOAP_QUERY_URL = 'https://cang.fa.us2.oraclecloud.com/analytics-ws/saw.dll?SoapImpl=xmlViewService'
    soap_envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v6="urn://oracle.bi.webservices/v6">
  <soapenv:Header/>
  <soapenv:Body>
    <v6:executeXMLQuery>
      <v6:report>
        <v6:reportPath>{REPORT_PATH}</v6:reportPath>
        <v6:reportXml></v6:reportXml>
      </v6:report>
      <v6:outputFormat></v6:outputFormat>
      <v6:executionOptions>
        <v6:async></v6:async>
        <v6:maxRowsPerPage></v6:maxRowsPerPage>
        <v6:refresh></v6:refresh>
        <v6:presentationInfo></v6:presentationInfo>
        <v6:type></v6:type>
      </v6:executionOptions>
      <v6:sessionID>{session_id}</v6:sessionID>
    </v6:executeXMLQuery>
  </soapenv:Body>
</soapenv:Envelope>'''
    headers = {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': '"urn://oracle.bi.webservices/v6/executeXMLQuery"'
    }
    try:
        response = requests.post(SOAP_QUERY_URL, data=soap_envelope, headers=headers)
        if response.status_code != 200:
            return []
        # Procesar XML
        root = ET.fromstring(response.text)
        soap_body = root.find('soapenv:Body', NAMESPACES)
        execute_result = soap_body.find('saw:executeXMLQueryResult', NAMESPACES)
        ret = execute_result.find('saw:return', NAMESPACES)
        rowset = ret.find('saw:rowset', NAMESPACES)
        query_result = rowset.text
        if not query_result:
            return []
        filas = re.findall(r'<Row>(.*?)</Row>', query_result, re.DOTALL)
        resultado = []
        carteras_vistas = set()  # Para trackear carteras únicas
        
        for fila_xml in filas:
            columnas = re.findall(r'<Column\d+>(.*?)</Column\d+>', fila_xml, re.DOTALL)
            if len(columnas) >= 2:
                cartera = columnas[0]
                year = columnas[1]
                
                # Extraer el año del mes (asumiendo formato YYYY-MM o similar)
                try:
                    # Intentar extraer año del formato de mes
                    año_match = re.search(r'(\d{4})', year)
                    if año_match:
                        año = int(año_match.group(1))
                        # Filtrar solo años 2024 y 2025
                        if año not in [2024, 2025]:
                            continue
                except:
                    pass  # Si no se puede extraer el año, incluir el registro
                
                # Solo agregar si la cartera no ha sido vista antes
                if cartera not in carteras_vistas:
                    carteras_vistas.add(cartera)
                    resultado.append({"id": f"{cartera}-{year}", "cartera": cartera, "year": year})

        return resultado
    except Exception as e:
        print(f"Error SOAP cartera-mes: {e}")
        return []

@router.get("/listar")
def listar_carteras():
    """
    Devuelve todas las carteras y año desde el reporte SOAP.
    """
    items = obtener_cartera_year()
    return {"items": items}

#TODO: Eliminar el user_id cuando se implemente el token
@router.get("/listar/usuario")
def listar_carteras_por_usuario(user_id: int, db: Session = Depends(get_db)):
    """
    Devuelve todas las carteras asociadas a un usuario específico (sin paginación).
    """
    rows = (
        db.query(CarteraModel.id, CarteraModel.nombre)
        .join(CarteraModel.usuarios)
        .filter(UsuarioModel.id == user_id)
        .all()
    )
    items = [{"id": r.id, "cartera": r.nombre} for r in rows]
    return {"items": items}
