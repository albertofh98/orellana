"""
Este módulo define el GeneratorAgent, responsable de generar respuestas
en lenguaje natural para el usuario basadas en los datos procesados y
el estado del grafo.
"""
import logging
import json
from services.graph_state import GraphState

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """
    Agente que genera texto de respuesta para el usuario, preparando el estado
    para respuestas en streaming o generando respuestas directas.
    """

    def __init__(self, model, prompts: dict, llm_helper_non_stream: callable,
                 llm_helper_stream: callable = None):
        self._model = model
        self.prompts = prompts
        self._call_llm_non_stream = llm_helper_non_stream
        self._call_llm_stream = llm_helper_stream

    def _prepare_response_state(self, state: GraphState, prompt_key: str,
                                node_name: str, replacements: dict) -> dict:
        """
        Prepara el estado para la generación de una respuesta, ya sea en streaming o no.
        """
        prompt_template = self.prompts[prompt_key]
        prompt_text = prompt_template
        for key, value in replacements.items():
            prompt_text = prompt_text.replace(key, str(value))

        return {
            "stream_generation_prompt": prompt_text,
            "stream_generation_node_name": node_name,
            "agent_response_text": None,
            "stream_completed_successfully": True,
            "error_message": state.get("error_message"),
            "last_stream_event_node": node_name
        }

    def generate_detailed_response(self, state: GraphState) -> dict:
        """
        Prepara una respuesta detallada sobre una convocatoria específica.
        """
        node_name = "generate_detailed_response_node"
        logger.info("Nodo: %s (preparando para stream)", node_name)

        detalles = state.get("api_response_data")
        detalles_texto = json.dumps(
            detalles, ensure_ascii=False, indent=2
        ) if detalles else "No se encontró la convocatoria."

        replacements = {
            "CHAT_HISTORY": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query'],
            "DETALLES_TEXTO": detalles_texto
        }
        return self._prepare_response_state(
            state, 'detailed_response', node_name, replacements
        )

    def generate_search_summary(self, state: GraphState) -> dict:
        """
        Prepara un resumen de los resultados de búsqueda de convocatorias.
        """
        node_name = "generate_search_summary_node"
        logger.info("Nodo: %s (preparando para stream)", node_name)

        resultados = state.get("api_response_data", {})
        num_items = resultados.get('itemCount', 0) if isinstance(
            resultados, dict
        ) else 0

        resumen_str = "No se encontraron resultados."
        if num_items > 0 and isinstance(resultados.get('content'), list):
            items = []
            for item in resultados['content']:
                items.append(
                    f"ID: {item.get('id')}, "
                    f"Num. Convocatoria: {item.get('numeroConvocatoria')}, "
                    f"Fecha: {item.get('fechaRecepcion')}, "
                    f"Título: {item.get('descripcion')}, "
                    f"Entidad: {item.get('nivel2')}"
                )
            resumen_str = "\n".join(items) if items else "Info no disponible."

        replacements = {
            "CHAT_HISTORY_STR": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query'],
            "API_CALL_PARAMS_JSON": json.dumps(
                state.get("api_call_params", {}), ensure_ascii=False
            ),
            "RESUMEN_PARA_PROMPT_STR": resumen_str,
            "{num_items}": str(num_items)
        }
        return self._prepare_response_state(
            state, 'search_summary', node_name, replacements
        )

    def generate_general_response(self, state: GraphState) -> dict:
        """
        Prepara una respuesta general o conversacional.
        """
        node_name = "generate_general_response_node"
        logger.info("Nodo: %s (preparando para stream)", node_name)

        replacements = {
            "CHAT_HISTORY_STR": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query']
        }
        return self._prepare_response_state(
            state, 'general_response', node_name, replacements
        )

    def generate_beneficiaries_summary(self, state: GraphState) -> dict:
        """
        Prepara un resumen de los datos de beneficiarios.
        """
        node_name = "generate_beneficiaries_summary_node"
        logger.info("Nodo: %s (preparando para stream)", node_name)

        beneficiaries_data = state.get("api_response_data")
        data_json = json.dumps(
            beneficiaries_data, ensure_ascii=False, indent=2
        ) if beneficiaries_data else "{}"

        replacements = {
            "ORIGINAL_QUERY": state['original_query'],
            "BENEFICIARIES_DATA_JSON": data_json
        }
        return self._prepare_response_state(
            state, 'beneficiaries_summary', node_name, replacements
        )

    def generate_parties_summary(self, state: GraphState) -> dict:
        """
        Prepara un resumen de los datos de partidos políticos.
        """
        node_name = "generate_parties_summary_node"
        logger.info("Nodo: %s (preparando para stream)", node_name)

        parties_data = state.get("api_response_data")
        data_json = json.dumps(
            parties_data, ensure_ascii=False, indent=2
        ) if parties_data else "{}"

        replacements = {
            "ORIGINAL_QUERY": state['original_query'],
            "PARTIES_DATA_JSON": data_json
        }
        return self._prepare_response_state(
            state, 'parties_summary', node_name, replacements
        )
