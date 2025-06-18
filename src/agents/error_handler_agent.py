# src/agents/error_handler_agent.py
import logging
from src.services.graph_state import GraphState

logger = logging.getLogger(__name__)


class ErrorHandlerAgent:
    def handle_error(self, state: GraphState) -> dict:
        node_name = "handle_error_node"
        error = state.get("error_message", "Un error desconocido ocurrió.")
        logger.error(f"Nodo: {node_name}, gestionando error: {error}")

        if "No pude identificar" in error:
            user_friendly_error = "No he podido identificar un ID de convocatoria. Por favor, inténtalo de nuevo."
        elif "No se encontraron detalles" in error:
            user_friendly_error = f"{error}. Por favor, verifica el número e inténtalo de nuevo."
        else:
            user_friendly_error = "Lo siento, ha ocurrido un problema técnico al procesar tu solicitud."

        return {
            "agent_response_text": user_friendly_error,
            "last_stream_event_node": node_name,
            "stream_completed_successfully": False
        }
