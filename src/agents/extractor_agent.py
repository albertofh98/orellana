"""
Este módulo define el ExtractorAgent, responsable de procesar la entrada del usuario
para extraer información clave como la intención, identificadores,
parámetros de búsqueda y otros datos relevantes utilizando un modelo de lenguaje.
"""
import logging
from services.graph_state import GraphState
from services.gemini_helpers import (
    generate_content_non_stream,
    parse_json_from_text,
)

logger = logging.getLogger(__name__)


class ExtractorAgent:
    """
    Agente que utiliza un modelo de lenguaje para extraer datos estructurados
    de las consultas del usuario y del historial de chat.
    """
    def __init__(self, model, prompts: dict):
        """
        Inicializa el agente con un modelo y plantillas de prompts.

        Args:
            model: El modelo de lenguaje a utilizar para la extracción.
            prompts (dict): Un diccionario de plantillas de prompts.
        """
        self._model = model
        self.prompts = prompts

    def determine_intent(self, state: GraphState) -> dict:
        """
        Determina la intención principal de la consulta del usuario.

        Args:
            state: El estado actual del grafo.

        Returns:
            Un diccionario con la intención determinada.
        """
        node_name = "determine_intent_node"
        original_query = state['original_query']
        logger.info("Nodo: %s, Consulta: %s", node_name, original_query)

        prompt = self.prompts['orchestrator'] \
            .replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history']) \
            .replace('ORIGINAL_QUERY', original_query)

        intent_response = generate_content_non_stream(self._model, prompt)
        intent = intent_response.strip()
        logger.info("Intención determinada: %s para '%s'", intent, original_query)

        valid_intents = [
            "OBTENER_CONVOCATORIA_DETALLES",
            "BUSCAR_CONVOCATORIAS_GENERAL",
            "BUSCAR_BENEFICIARIOS_POR_ANNO",
            "GENERAL_CONVERSATION",
            "BUSCAR_PARTIDOS_POLITICOS"
        ]
        if intent not in valid_intents:
            logger.warning(
                "Intención no válida '%s', usando GENERAL_CONVERSATION por defecto.",
                intent
            )
            intent = "GENERAL_CONVERSATION"
        return {"intent": intent, "last_stream_event_node": node_name}

    def extract_convocatoria_id(self, state: GraphState) -> dict:
        """
        Extrae un ID de convocatoria de la consulta del usuario.

        Args:
            state: El estado actual del grafo.

        Returns:
            Un diccionario con el ID extraído o un mensaje de error.
        """
        node_name = "extract_convocatoria_id_node"
        prompt = self.prompts['extractor'] \
            .replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history']) \
            .replace('ORIGINAL_QUERY', state['original_query'])

        id_text = generate_content_non_stream(self._model, prompt)
        error_msg, extracted_id = None, None

        if id_text.startswith("ERROR_"):
            error_msg = f"Error del modelo al extraer ID: {id_text}"
        else:
            extracted_id = id_text.strip()
            if extracted_id == "NO_ID" or not extracted_id:
                error_msg = ("No pude identificar el número de la convocatoria "
                             "en tu consulta.")
                extracted_id = None
            else:
                logger.info("ID de convocatoria extraído: %s", extracted_id)

        return {
            "extracted_convocatoria_id": extracted_id,
            "error_message": error_msg,
            "last_stream_event_node": node_name
        }

    def extract_search_params(self, state: GraphState) -> dict:
        """
        Extrae parámetros de búsqueda para convocatorias de la consulta.

        Args:
            state: El estado actual del grafo.

        Returns:
            Un diccionario con los parámetros para la API o un mensaje de error.
        """
        node_name = "extract_search_params_node"
        query = state['original_query']
        logger.info(
            "Nodo: %s, Consulta original para extraer parámetros: '%s'",
            node_name, query
        )
        prompt_template = self.prompts.get('search_params')
        if not prompt_template:
            logger.error(
                "%s: Prompt 'search_params' no encontrado en self.prompts.", node_name
            )
            return {
                "api_call_params": None,
                "error_message": "Error interno: Falta la plantilla de prompt.",
                "last_stream_event_node": node_name
            }

        prompt = prompt_template \
            .replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history']) \
            .replace('ORIGINAL_QUERY', query)
        logger.debug(
            "Prompt para extracción (extract_search_params):\n%s", prompt
        )

        params_text = generate_content_non_stream(self._model, prompt)
        parsed_json = parse_json_from_text(params_text, default_if_error={})
        logger.info(
            "Parámetros parseados del LLM (extract_search_params): %s", parsed_json
        )

        api_params, error_msg = None, None

        if not parsed_json:
            error_msg = "No se pudieron determinar parámetros de búsqueda válidos."
            logger.warning("%s: %s (LLM output: '%s')",
                         node_name, error_msg, params_text)
        else:
            api_params = {
                'page': parsed_json.get('page', '0'),
                'pageSize': parsed_json.get('pageSize', '50'),
                'descripcion': parsed_json.get('descripcion', '').strip(),
                'descripcionTipoBusqueda': parsed_json.get(
                    'descripcionTipoBusqueda', '1'
                )
            }
            if parsed_json.get('fechaDesde'):
                api_params['fechaDesde'] = parsed_json['fechaDesde']
            if parsed_json.get('fechaHasta'):
                api_params['fechaHasta'] = parsed_json['fechaHasta']

            if not api_params['descripcion'] and query:
                logger.info(
                    "%s: Descripción vacía, usando consulta original '%s'.",
                    node_name, query
                )
                api_params['descripcion'] = query
            if not api_params['descripcion']:
                error_msg = "No se proporcionó un término de búsqueda."
                logger.warning("%s: %s", node_name, error_msg)
                api_params = None

        if error_msg and not api_params:
            logger.warning(
                "%s: Error final, api_params es None. Error: %s",
                node_name, error_msg
            )
        logger.info(
            "%s: Parámetros finales para la API: %s", node_name, api_params
        )
        return {
            "api_call_params": api_params,
            "error_message": error_msg,
            "last_stream_event_node": node_name
        }

    def extract_years(self, state: GraphState) -> dict:
        """
        Extrae una lista de años de la consulta del usuario.

        Args:
            state: El estado actual del grafo.

        Returns:
            Un diccionario con una cadena de años separados por comas.
        """
        node_name = "extract_years_node"
        original_query = state['original_query']
        logger.info("Nodo: %s, Consulta: %s", node_name, original_query)

        prompt = self.prompts['extract_years'] \
            .replace('FORMATTED_CHAT_HISTORY', state['formatted_chat_history']) \
            .replace('ORIGINAL_QUERY', original_query)
        logger.info("Prompt para extracción de años: %s", prompt)

        extracted_years = generate_content_non_stream(self._model, prompt)
        error_msg = None

        if not isinstance(extracted_years, str) or not extracted_years:
            error_msg = ("No pude identificar ningún año en tu consulta. "
                         "Por favor, sé más claro (ej: 'beneficiarios de 2023').")
            extracted_years = None
        else:
            logger.info("Años extraídos: %s", extracted_years)

        return {
            "extracted_years": extracted_years,
            "error_message": error_msg,
            "last_stream_event_node": node_name
        }

    def extract_party_params(self, state: GraphState) -> dict:
        """
        Extrae parámetros para buscar un partido político.

        Args:
            state: El estado actual del grafo.

        Returns:
            Un diccionario con los parámetros para la API o un mensaje de error.
        """
        node_name = "extract_party_params_node"
        query = state['original_query']
        logger.info(
            "Nodo: %s, extrayendo params para buscar partido de: '%s'",
            node_name, query
        )
        prompt = self.prompts['extract_party_params'].replace('ORIGINAL_QUERY', query)
        params_text = generate_content_non_stream(self._model, prompt)
        parsed_json = parse_json_from_text(params_text, default_if_error={})
        logger.info(
            "Params extraídos del LLM (extract_party_params): %s", parsed_json
        )

        if not parsed_json or not parsed_json.get("beneficiario"):
            return {
                "error_message": ("No pude identificar el nombre del partido en tu "
                                "consulta."),
                "last_stream_event_node": node_name
            }
        return {
            "api_call_params": {
                "nombre": parsed_json.get("beneficiario"),
                "fechaDesde": parsed_json.get("fechaDesde", ""),
                "fechaHasta": parsed_json.get("fechaHasta", "")
            },
            "last_stream_event_node": node_name
        }
