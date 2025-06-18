import logging
import json
from src.services.graph_state import GraphState
from src.services.infosubvenciones_service import info_subvenciones_service

logger = logging.getLogger(__name__)


class PoliticalPartiesAgent:
    def __init__(self):
        self.infosubvenciones_service = info_subvenciones_service

    def search_parties(self, state: GraphState) -> dict:
        node_name = "search_political_parties_node"
        params = state.get("api_call_params")
        if not params:
            logger.warning(f"{node_name}: No se proporcionó un nombre de partido para la búsqueda.")
            return {
                "error_message": "Por favor, especifica el nombre del partido político que deseas buscar.",
                "last_stream_event_node": node_name
            }

        try:
            logger.info(f"{node_name}: Llamando a infosubvenciones_service.buscar_partidos_politicos con params: {params}")
            api_response = self.infosubvenciones_service.buscar_partidos_politicos(params)
            logger.info(f"{node_name}: Respuesta de la API: {json.dumps(api_response, indent=2)}")

            return {
                "api_response_data": api_response,
                "last_stream_event_node": node_name
            }

        except Exception as e:
            error_msg = f"Error crítico al llamar a la API de partidos políticos: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "error_message": error_msg,
                "last_stream_event_node": node_name
            }
