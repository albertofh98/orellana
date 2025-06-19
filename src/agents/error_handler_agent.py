"""
Este módulo define el agente manejador de errores.

Su propósito es interceptar los errores ocurridos en el grafo,
traducirlos a mensajes amigables para el usuario y finalizar el flujo
de manera controlada.
"""
import logging
from services.graph_state import GraphState

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class ErrorHandlerAgent:
    """
    Agente encargado de gestionar los errores producidos durante la ejecución del grafo.
    """
    def handle_error(self, state: GraphState) -> dict:
        """
        Gestiona un error del estado, lo registra y devuelve un mensaje para el usuario.

        Args:
            state: El estado actual del grafo, que se espera que contenga un 'error_message'.

        Returns:
            Un diccionario con el texto de respuesta para el usuario y el estado final del stream.
        """
        node_name = "handle_error_node"
        error = state.get("error_message", "Un error desconocido ocurrió.")
        logger.error("Nodo: %s, gestionando error: %s", node_name, error)

        if "No pude identificar" in error:
            user_friendly_error = (
                "No he podido identificar un ID de convocatoria. "
                "Por favor, inténtalo de nuevo."
            )
        elif "No se encontraron detalles" in error:
            user_friendly_error = (
                f"{error}. Por favor, verifica el número e inténtalo de nuevo."
            )
        else:
            user_friendly_error = (
                "Lo siento, ha ocurrido un problema técnico al procesar tu solicitud."
            )

        return {
            "agent_response_text": user_friendly_error,
            "last_stream_event_node": node_name,
            "stream_completed_successfully": False
        }
