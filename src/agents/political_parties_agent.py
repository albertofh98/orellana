"""
Este módulo define el PoliticalPartiesAgent, responsable de interactuar
con el servicio de subvenciones para buscar información sobre partidos políticos.
"""
import logging
import json
from src.services.graph_state import GraphState
from src.services.infosubvenciones_service import info_subvenciones_service

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class PoliticalPartiesAgent:
    """
    Agente encargado de realizar búsquedas de partidos políticos a través del
    servicio de InfoSubvenciones.
    """
    def __init__(self):
        """Inicializa el agente y el servicio de subvenciones."""
        self.infosubvenciones_service = info_subvenciones_service

    def search_parties(self, state: GraphState) -> dict:
        """
        Busca partidos políticos utilizando los parámetros del estado.

        Args:
            state: El estado actual del grafo, que contiene los parámetros de la API.

        Returns:
            Un diccionario con los datos de la respuesta de la API o un mensaje de error.
        """
        node_name = "search_political_parties_node"
        params = state.get("api_call_params")
        if not params:
            logger.warning(
                "%s: No se proporcionó un nombre de partido para la búsqueda.",
                node_name
            )
            return {
                "error_message": "Por favor, especifica el nombre del partido.",
                "last_stream_event_node": node_name
            }

        try:
            logger.info(
                "%s: Llamando a buscar_partidos_politicos con params: %s",
                node_name, params
            )
            api_response = self.infosubvenciones_service.buscar_partidos_politicos(
                params
            )
            logger.info(
                "%s: Respuesta de la API: %s",
                node_name, json.dumps(api_response, indent=2)
            )

            return {
                "api_response_data": api_response,
                "last_stream_event_node": node_name
            }

        # pylint: disable=broad-exception-caught
        except Exception as e:
            error_msg = f"Error crítico al llamar a la API de partidos: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "error_message": error_msg,
                "last_stream_event_node": node_name
            }
