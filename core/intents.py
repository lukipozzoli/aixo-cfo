from enum import Enum


class Intent(str, Enum):
    # Todos los intents posibles del sistema.
    # Usando str como base para que cada valor sea comparable directamente con strings.
    # El Router clasifica cada mensaje entrante en uno de estos valores.

    CONSULTA_INFORMACION = "consulta_informacion"
    CONSULTA_ARCHIVO = "consulta_archivo"
    REPORTE = "reporte"
    PROYECCION = "proyeccion"
    INVESTIGACION = "investigacion"
    CONCILIACION = "conciliacion"
    EDICION_DB = "edicion_db"
    CONFIGURACION_ALERTA = "configuracion_alerta"
    EVENTO_EXTERNO = "evento_externo"
    RESPUESTA_AGENTE = "respuesta_agente"
    CONVERSACIONAL = "conversacional"
    DESCONOCIDO = "desconocido"
