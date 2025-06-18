import logging
from src.services.graph_state import GraphState


logger = logging.getLogger(__name__)


class ApiCallerAgent:
    def __init__(self, infosubvenciones_service):
        self.infosubvenciones_service = infosubvenciones_service

    def get_details(self, state: GraphState) -> dict:
        # ... (código existente, se mantiene igual)
        node_name = "call_infosubvenciones_get_details_node"
        conv_id = state.get("extracted_convocatoria_id")

        if not conv_id or conv_id == "NO_ID":
            return {"error_message": "No se pudo identificar un ID de convocatoria válido en la consulta.",
                    "last_stream_event_node": node_name}

        try:
            data = self.infosubvenciones_service.obtener_convocatoria(conv_id)
            actual_item = None
            # Caso 1: La API de detalle puede devolver
            # el objeto directamente si no es parte de una búsqueda
            # o una estructura con 'idConvocatoriaBDNS'
            # u otro identificador único.
            # Esta lógica puede necesitar ajuste basado
            # en la respuesta real de obtener_convocatoria(id).
            if isinstance(data, dict) \
                and not ('content' in data or 'itemCount' in data):
                actual_item = data
            # Caso 2: La API de detalle envuelve el resultado
            # en una estructura similar a la de búsqueda
            elif isinstance(data, dict) and 'content' in data:
                if isinstance(data['content'], list) and data['content']:
                    actual_item = data['content'][0]
            elif isinstance(data, list) and data:
                actual_item = data[0]

            if actual_item is None:
                return {"error_message": f"No se encontraron detalles claros para el ID '{conv_id}'.",
                        "api_response_data": data,
                        "last_stream_event_node": node_name}

            return {"api_response_data": actual_item, "last_stream_event_node": node_name}

        except IndexError as e:
            return {"error_message": f"Error de API al obtener detalles para ID '{conv_id}': {e}",
                    "last_stream_event_node": node_name}

    def search(self, state: GraphState) -> dict:
        node_name = "call_infosubvenciones_search_node"
        params = state.get("api_call_params")

        if not params:
            return {
                "error_message": "No se pudieron determinar \
                    los parámetros para realizar la búsqueda.",
                "api_response_data": {"itemCount": 0,
                                      "content": [],
                                      "totalElements": 0},
                "last_stream_event_node": node_name
            }

        try:
            data = self.infosubvenciones_service.buscar_convocatorias(params)
            total_elements_available = 0

            if isinstance(data, dict):
                total_elements_available = data.get('totalElements', 0)
                # Para la lógica del prompt, 'itemCount'
                # debería reflejar el total de elementos encontrados,
                # no solo los de la página actual,
                # para dar una idea completa.
                # Si 'totalElements' está disponible, usarlo.
                # Si no, usar los de la página actual.
                # El prompt usa NUM_ITEMS que se reemplaza por
                # 'itemCount' que pongamos en api_response_data.
                # Así que vamos a asegurar que 'itemCount' en
                # 'api_response_data' sea el total.
                data['itemCount'] = total_elements_available
            else:
                return {
                    "api_response_data": {"itemCount": 0, "content": [],
                                          "totalElements": 0,
                                          "error": "Respuesta API no es un diccionario"},
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
                "api_response_data": {"itemCount": 0,
                                      "content": [],
                                      "totalElements": 0,
                                      "error": str(e)},
                "last_stream_event_node": node_name}
