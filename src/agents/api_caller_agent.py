"""
Este módulo define el agente encargado de realizar llamadas a la API de InfoSubvenciones.
"""
import logging
from services.graph_state import GraphState


logger = logging.getLogger(__name__)


class ApiCallerAgent:
    """
    Agente que interactúa con el servicio de InfoSubvenciones para buscar y obtener
    detalles de convocatorias.
    """
    def __init__(self, infosubvenciones_service):
        self.infosubvenciones_service = infosubvenciones_service

    def get_details(self, state: GraphState) -> dict:
        """
        Obtiene los detalles de una convocatoria específica usando su ID.

        Args:
            state (GraphState): El estado actual del grafo que contiene el ID de la convocatoria.

        Returns:
            dict: Un diccionario con los datos de la respuesta de la API o un mensaje de error.
        """
        node_name = "call_infosubvenciones_get_details_node"
        conv_id = state.get("extracted_convocatoria_id")

        if not conv_id or conv_id == "NO_ID":
            return {
                "error_message": "No se pudo identificar ID de convocatoria válido en la consulta.",
                "last_stream_event_node": node_name
            }

        try:
            data = self.infosubvenciones_service.obtener_convocatoria(conv_id)
            actual_item = None
            # Caso 1: La API puede devolver el objeto directamente.
            if isinstance(data, dict) and not ('content' in data or 'itemCount' in data):
                actual_item = data
            # Caso 2: La API envuelve el resultado en una estructura similar a la de búsqueda.
            elif isinstance(data, dict) and 'content' in data:
                if isinstance(data['content'], list) and data['content']:
                    actual_item = data['content'][0]
            elif isinstance(data, list) and data:
                actual_item = data[0]

            if actual_item is None:
                return {
                    "error_message": f"No se encontraron detalles para el ID '{conv_id}'.",
                    "api_response_data": data,
                    "last_stream_event_node": node_name
                }

            return {"api_response_data": actual_item, "last_stream_event_node": node_name}

        except IndexError as e:
            return {
                "error_message": f"Error de API al obtener detalles para ID '{conv_id}': {e}",
                "last_stream_event_node": node_name
            }

    def search(self, state: GraphState) -> dict:
        """
        Realiza una búsqueda de convocatorias basada en los parámetros del estado.

        Args:
            state (GraphState): El estado actual del grafo que contiene los parámetros de búsqueda.

        Returns:
            dict: Un diccionario con los resultados de la búsqueda o un mensaje de error.
        """
        node_name = "call_infosubvenciones_search_node"
        params = state.get("api_call_params")

        if not params:
            return {
                "error_message": "No se pudieron determinar los parámetros para la búsqueda.",
                "api_response_data": {
                    "itemCount": 0, "content": [], "totalElements": 0
                },
                "last_stream_event_node": node_name
            }

        try:
            data = self.infosubvenciones_service.buscar_convocatorias(params)
            total_elements_available = 0

            if isinstance(data, dict):
                total_elements_available = data.get('totalElements', 0)
                # Aseguramos que 'itemCount' refleje el total de elementos encontrados
                # para dar una idea completa de la magnitud de los resultados.
                data['itemCount'] = total_elements_available
            else:
                return {
                    "api_response_data": {
                        "itemCount": 0, "content": [], "totalElements": 0,
                        "error": "Respuesta API no es un diccionario"
                    },
                    "last_stream_event_node": node_name
                }

            if total_elements_available == 0:
                return {
                    "api_response_data": data,
                    "last_stream_event_node": node_name
                }
            return {
                "api_response_data": data,
                "last_stream_event_node": node_name
            }

        except IndexError as e:
            return {
                "error_message": f"Error de API al buscar convocatorias: {e}",
                "api_response_data": {
                    "itemCount": 0, "content": [], "totalElements": 0, "error": str(e)
                },
                "last_stream_event_node": node_name
            }
