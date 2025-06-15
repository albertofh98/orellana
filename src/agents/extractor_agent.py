# src/agents/extractor_agent.py
import logging
from src.services.graph_state import GraphState
from src.services.gemini_helpers import generate_content_non_stream, parse_json_from_text

logger = logging.getLogger(__name__)

class ExtractorAgent:
    def __init__(self, model, prompts: dict):
        self._model = model
        self.prompts = prompts

    def determine_intent(self, state: GraphState) -> dict:
        node_name = "determine_intent_node"
        logger.info(f"Nodo: {node_name}, Consulta: {state['original_query']}")
        
        prompt = self.prompts['orchestrator'].replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history'])\
                                            .replace('ORIGINAL_QUERY', state['original_query'])
                                            
        intent_response = generate_content_non_stream(self._model, prompt)
        intent = intent_response.strip()
        logger.info(f"Intención determinada: {intent} para '{state['original_query']}'")

        valid_intents = ["OBTENER_CONVOCATORIA_DETALLES", "BUSCAR_CONVOCATORIAS_GENERAL", 
                         "BUSCAR_BENEFICIARIOS_POR_ANNO", "GENERAL_CONVERSATION"]
        if intent not in valid_intents:
            logger.warning(f"Intención no válida '{intent}', usando GENERAL_CONVERSATION por defecto.")
            intent = "GENERAL_CONVERSATION"
        return {"intent": intent, "last_stream_event_node": "determine_intent_node"}

    def extract_convocatoria_id(self, state: GraphState) -> dict:
        node_name = "extract_convocatoria_id_node"
        prompt = self.prompts['extractor'].replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history'])\
                                          .replace('ORIGINAL_QUERY', state['original_query'])

        id_text = generate_content_non_stream(self._model, prompt)
        error_msg, extracted_id = None, None

        if id_text.startswith("ERROR_"):
            error_msg = f"Error del modelo al extraer ID: {id_text}"
        else:
            extracted_id = id_text.strip()
            if extracted_id == "NO_ID" or not extracted_id:
                error_msg = "No pude identificar el número de la convocatoria en tu consulta."
                extracted_id = None
            else:
                logger.info(f"ID de convocatoria extraído: {extracted_id}")
        
        return {"extracted_convocatoria_id": extracted_id, "error_message": error_msg, "last_stream_event_node": node_name}

    def extract_search_params(self, state: GraphState) -> dict:
        node_name = "extract_search_params_node"
        query = state['original_query']
        logger.info(f"Nodo: {node_name}, Consulta original para extraer parámetros: '{query}'")
        
        prompt_template = self.prompts.get('search_params') # Usar .get para evitar KeyError si falta el prompt
        if not prompt_template:
            logger.error(f"{node_name}: Prompt 'search_params' no encontrado en self.prompts.")
            return {
                "api_call_params": None,
                "error_message": "Error interno: Falta la plantilla de prompt para extraer parámetros de búsqueda.",
                "last_stream_event_node": node_name
            }

        prompt = prompt_template.replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history'])\
                                .replace('ORIGINAL_QUERY', query)
        
        logger.debug(f"Prompt para extracción de parámetros de búsqueda (extract_search_params):\n{prompt}")

        params_text_from_llm = generate_content_non_stream(self._model, prompt)

        # parse_json_from_text ya maneja si params_text_from_llm es un error o no contiene JSON válido
        parsed_llm_json = parse_json_from_text(params_text_from_llm, default_if_error={}) # Devuelve {} si falla
        
        logger.info(f"Parámetros de búsqueda parseados del JSON del LLM (extract_search_params): {parsed_llm_json}")

        api_params_to_send = None
        error_msg = None

        if not parsed_llm_json: # Si parse_json_from_text devolvió {} o None (y el default es {})
            # Esto puede ocurrir si el LLM no devuelve un JSON válido o devuelve una cadena vacía/error
            error_msg = "No se pudieron determinar parámetros de búsqueda válidos a partir de tu consulta. Intenta ser más específico."
            logger.warning(f"{node_name}: {error_msg} (LLM output: '{params_text_from_llm}')")
        else:
            # Construir los parámetros finales para la API
            # Usar valores por defecto razonables si el LLM no los proporciona todos
            api_params_to_send = {
                'page': parsed_llm_json.get('page', '0'), # Permitir que el LLM sugiera página/tamaño si es avanzado
                'pageSize': parsed_llm_json.get('pageSize', '50'), # Default a 10 para resumen inicial
                'descripcion': parsed_llm_json.get('descripcion', '').strip(),
                'descripcionTipoBusqueda': parsed_llm_json.get('descripcionTipoBusqueda', '1') # Default '1' (Todas las palabras)
            }
            # Solo añadir fechas si están presentes y son válidas (el LLM debe devolver formato DD/MM/YYYY)
            if parsed_llm_json.get('fechaDesde'):
                api_params_to_send['fechaDesde'] = parsed_llm_json['fechaDesde']
            if parsed_llm_json.get('fechaHasta'):
                api_params_to_send['fechaHasta'] = parsed_llm_json['fechaHasta']
            
            # Si la descripción está vacía después de todo, podríamos usar la consulta original como fallback,
            # o decidir que no es una búsqueda válida.
            if not api_params_to_send['descripcion'] and query:
                logger.info(f"{node_name}: Descripción extraída vacía, usando consulta original '{query}' como descripción.")
                api_params_to_send['descripcion'] = query # Fallback a la consulta original si no hay descripción específica

            if not api_params_to_send['descripcion']: # Si sigue vacía
                 error_msg = "No se proporcionó un término de búsqueda (descripción) para las convocatorias."
                 logger.warning(f"{node_name}: {error_msg}")
                 api_params_to_send = None # Invalidar parámetros si no hay descripción

        if error_msg and not api_params_to_send : # Si hubo un error que invalidó los params
             logger.warning(f"{node_name}: Error final al extraer parámetros, api_params_to_send es None. Error: {error_msg}")


        logger.info(f"{node_name}: Parámetros finales que se enviarán a la API (api_call_params): {api_params_to_send}")
        return {
            "api_call_params": api_params_to_send, # Será None si la extracción falló críticamente
            "error_message": error_msg, # Puede haber un error_msg aunque haya api_params (ej. fallback usado)
            "last_stream_event_node": node_name
        }
    
    def extract_years(self, state: GraphState) -> dict:
        node_name = "extract_years_node"
        logger.info(f"Nodo: {node_name}, Consulta: {state['original_query']}")
        
        prompt = self.prompts['extract_years'].replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history'])\
                                              .replace('ORIGINAL_QUERY', state['original_query'])
        logger.info(f"Prompt para extracción de años: {prompt}")
        
        extracted_years = generate_content_non_stream(self._model, prompt)
        error_msg = None

        if not isinstance(extracted_years, str) or not extracted_years:
            error_msg = "No pude identificar ningún año específico en tu consulta. Por favor, sé más claro (ej: 'beneficiarios de 2023')."
            extracted_years = None
        else:
            logger.info(f"Años extraídos: {extracted_years}")

        return {"extracted_years": extracted_years, "error_message": error_msg, "last_stream_event_node": node_name}