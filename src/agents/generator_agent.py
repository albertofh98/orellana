# src/agents/generator_agent.py
import logging
import json
# from typing import Optional, Tuple # Ya no se usa directamente aquí para la salida de los helpers
from src.services.graph_state import GraphState

logger = logging.getLogger(__name__)

class GeneratorAgent:
    # El constructor ahora solo necesita el helper non-stream para respuestas de error o simples
    def __init__(self, model, prompts: dict, llm_helper_non_stream: callable, llm_helper_stream: callable = None):
        self._model = model
        self.prompts = prompts
        self._call_llm_for_generation_non_stream = llm_helper_non_stream
        self._call_llm_for_generation_stream = llm_helper_stream # Lo guardamos para usarlo en LangGraphService

    # CAMBIO: generate_detailed_response y los otros ahora preparan para streaming
    # en lugar de devolver el stream ellos mismos.
    def _prepare_response_state(self, state: GraphState, prompt_template_key: str, node_name: str, 
                                replacements: dict, is_streamable: bool = True) -> dict:
        
        current_prompt_template = self.prompts[prompt_template_key]
        
        # Llenar el prompt con las sustituciones necesarias
        prompt_text = current_prompt_template
        for key, value in replacements.items():
            prompt_text = prompt_text.replace(key, str(value)) # Asegurar que los valores sean strings

        if is_streamable:
            # Si es streamable, guardamos el prompt para que LangGraphService lo use
            return {
                "stream_generation_prompt": prompt_text,
                "stream_generation_node_name": node_name,
                "agent_response_text": None, # No hay texto pre-generado
                "stream_completed_successfully": True, # Asumimos que la preparación fue exitosa
                "error_message": state.get("error_message"), # Propagar errores existentes
                "last_stream_event_node": node_name
            }
        else:
            # Si no es streamable (ej. una respuesta de error o muy simple), la generamos directamente
            text, success, err = self._call_llm_for_generation_non_stream(self._model, prompt_text, node_name)
            return {
                "agent_response_text": text, 
                "stream_completed_successfully": success, 
                "error_message": err or state.get("error_message"), # Combinar errores
                "last_stream_event_node": node_name,
                "stream_generation_prompt": None # No hay stream
            }

    def generate_detailed_response(self, state: GraphState) -> dict:
        node_name = "generate_detailed_response_node"
        logger.info(f"Nodo: {node_name} (preparando para stream o generando directamente)")
        
        detalles = state.get("api_response_data")
        detalles_texto = json.dumps(detalles, ensure_ascii=False, indent=2) if detalles else "No se encontró la convocatoria."
        
        # Si hay un error por no encontrar la convocatoria, podríamos generar una respuesta directa
        # en lugar de intentar un stream.
        # Por ahora, asumimos que siempre es streamable.
        
        replacements = {
            "CHAT_HISTORY": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query'],
            "DETALLES_TEXTO": detalles_texto
        }
        return self._prepare_response_state(state, 'detailed_response', node_name, replacements)

    def generate_search_summary(self, state: GraphState) -> dict:
        node_name = "generate_search_summary_node"
        logger.info(f"Nodo: {node_name} (preparando para stream o generando directamente)")

        resultados = state.get("api_response_data", {})
        num_items = resultados.get('itemCount', 0) if isinstance(resultados, dict) else 0
        
        resumen_str = "No se encontraron resultados."
        if num_items > 0 and isinstance(resultados.get('content'), list):
            # Simplificar para el prompt, el LLM puede formatear la tabla
            items_for_prompt = []
            for item in resultados['content']:
                items_for_prompt.append(f"ID: {item.get('id')}, \
                                        Num. Convocatoria: {item.get('numeroConvocatoria')}, \
                                        Fecha: {item.get('fechaRecepcion')}, \
                                        Título: {item.get('descripcion')}, \
                                        Entidad: {item.get('nivel2')}")
            resumen_str = "\n".join(items_for_prompt) if items_for_prompt else "Información de resumen no disponible."

        replacements = {
            "CHAT_HISTORY_STR": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query'],
            "API_CALL_PARAMS_JSON": json.dumps(state.get("api_call_params", {}), ensure_ascii=False), # Añadido por el prompt
            "RESUMEN_PARA_PROMPT_STR": resumen_str,
            "{num_items}": str(num_items) # Corregido de NUM_ITEMS a {num_items} según el prompt
        }
        return self._prepare_response_state(state, 'search_summary', node_name, replacements)

    def generate_general_response(self, state: GraphState) -> dict:
        node_name = "generate_general_response_node"
        logger.info(f"Nodo: {node_name} (preparando para stream o generando directamente)")
        
        replacements = {
            "CHAT_HISTORY_STR": state['formatted_chat_history'],
            "ORIGINAL_QUERY": state['original_query']
        }
        # Las respuestas generales suelen ser cortas, podríamos hacerlas no-stream por defecto
        # return self._prepare_response_state(state, 'general_response', node_name, replacements, is_streamable=False)
        # O mantenerlas streamable si pueden ser largas
        return self._prepare_response_state(state, 'general_response', node_name, replacements)
    
    def generate_beneficiaries_summary(self, state: GraphState) -> dict:
        node_name = "generate_beneficiaries_summary_node"
        logger.info(f"Nodo: {node_name} (preparando para stream)")
        
        beneficiaries_data = state.get("api_response_data")
        data_json = json.dumps(beneficiaries_data, ensure_ascii=False, indent=2) if beneficiaries_data else "{}"

        replacements = {
            "ORIGINAL_QUERY": state['original_query'],
            "BENEFICIARIES_DATA_JSON": data_json
        }
        return self._prepare_response_state(state, 'beneficiaries_summary', node_name, replacements)