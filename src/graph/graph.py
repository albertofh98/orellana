"""
Este módulo define la estructura y el flujo de control del grafo de LangGraph.

Contiene las funciones de enrutamiento condicional y la función principal
para construir el grafo que orquesta a los agentes.
"""
import logging
from langgraph.graph import END, StateGraph
from services.graph_state import GraphState

logger = logging.getLogger(__name__)


def should_extract(state: GraphState) -> str:
    """
    Decide el siguiente nodo de extracción basado en la intención determinada.

    Args:
        state: El estado actual del grafo.

    Returns:
        El nombre del siguiente nodo a ejecutar.
    """
    if state.get("error_message"):
        return "error_handler"
    intent_map = {
        "OBTENER_CONVOCATORIA_DETALLES": "extract_convocatoria_id_node",
        "BUSCAR_CONVOCATORIAS_GENERAL": "extract_search_params_node",
        "BUSCAR_BENEFICIARIOS_POR_ANNO": "extract_years_node",
        "BUSCAR_PARTIDOS_POLITICOS": "extract_party_params_node",
        "GENERAL_CONVERSATION": "generate_general_response_node"
    }
    return intent_map.get(state["intent"], "error_handler")


def should_call_api(state: GraphState) -> str:
    """
    Decide qué nodo de llamada a la API ejecutar basado en la intención.

    Args:
        state: El estado actual del grafo.

    Returns:
        El nombre del nodo de la API o el manejador de errores.
    """
    if state.get("error_message"):
        return "error_handler"

    intent = state["intent"]
    if intent == "OBTENER_CONVOCATORIA_DETALLES":
        return "call_infosubvenciones_get_details_node"
    if intent == "BUSCAR_CONVOCATORIAS_GENERAL":
        return "call_infosubvenciones_search_node"
    if intent == "BUSCAR_BENEFICIARIOS_POR_ANNO":
        return "get_beneficiaries_node"
    if intent == "BUSCAR_PARTIDOS_POLITICOS":
        return "search_political_parties_node"
    return "error_handler"


def should_generate_response(state: GraphState) -> str:
    """
    Decide qué nodo generador de respuesta usar según la intención.

    Args:
        state: El estado actual del grafo.

    Returns:
        El nombre del nodo generador o el manejador de errores.
    """
    error_msg = state.get("error_message") or ""
    if "Error de API" in error_msg:
        return "error_handler"

    intent = state["intent"]
    if intent == "OBTENER_CONVOCATORIA_DETALLES":
        return "generate_detailed_response_node"
    if intent == "BUSCAR_CONVOCATORIAS_GENERAL":
        return "generate_search_summary_node"
    if intent == "BUSCAR_BENEFICIARIOS_POR_ANNO":
        return "generate_beneficiaries_summary_node"
    if intent == "BUSCAR_PARTIDOS_POLITICOS":
        return "generate_parties_summary_node"
    return "error_handler"


def build_agent_graph(agents: dict) -> StateGraph:
    """
    Construye y configura el StateGraph con todos los nodos y aristas.

    Args:
        agents: Un diccionario que contiene las instancias de los agentes.

    Returns:
        Una instancia del StateGraph compilado.
    """
    workflow = StateGraph(GraphState)
    # Añadir nodos
    workflow.add_node("determine_intent_node", agents['extractor'].determine_intent)
    workflow.add_node("extract_convocatoria_id_node",
                      agents['extractor'].extract_convocatoria_id)
    workflow.add_node("extract_search_params_node",
                      agents['extractor'].extract_search_params)
    workflow.add_node("call_infosubvenciones_get_details_node",
                      agents['api_caller'].get_details)
    workflow.add_node("call_infosubvenciones_search_node",
                      agents['api_caller'].search)
    workflow.add_node("generate_detailed_response_node",
                      agents['generator'].generate_detailed_response)
    workflow.add_node("generate_search_summary_node",
                      agents['generator'].generate_search_summary)
    workflow.add_node("generate_general_response_node",
                      agents['generator'].generate_general_response)
    workflow.add_node("error_handler", agents['error_handler'].handle_error)
    workflow.add_node("extract_party_params_node",
                      agents['extractor'].extract_party_params)
    workflow.add_node("search_political_parties_node",
                      agents['political_parties'].search_parties)
    workflow.add_node("generate_parties_summary_node",
                      agents['generator'].generate_parties_summary)
    workflow.add_node("extract_years_node", agents['extractor'].extract_years)
    workflow.add_node("get_beneficiaries_node",
                      agents['beneficiaries'].get_beneficiaries_by_year)
    workflow.add_node("generate_beneficiaries_summary_node",
                      agents['generator'].generate_beneficiaries_summary)

    # Definir aristas y punto de entrada
    workflow.set_entry_point("determine_intent_node")
    workflow.add_conditional_edges("determine_intent_node", should_extract)
    workflow.add_conditional_edges(
        "extract_convocatoria_id_node", should_call_api)
    workflow.add_conditional_edges(
        "extract_search_params_node", should_call_api)
    workflow.add_conditional_edges("extract_years_node", should_call_api)
    workflow.add_conditional_edges(
        "call_infosubvenciones_get_details_node", should_generate_response)
    workflow.add_conditional_edges(
        "call_infosubvenciones_search_node", should_generate_response)
    workflow.add_conditional_edges(
        "get_beneficiaries_node", should_generate_response)
    workflow.add_conditional_edges(
        "extract_party_params_node", should_call_api)
    workflow.add_conditional_edges(
        "search_political_parties_node", should_generate_response)

    # Todos los nodos finales terminan el grafo
    end_nodes = [
        "generate_detailed_response_node", "generate_search_summary_node",
        "generate_general_response_node", "error_handler",
        "generate_beneficiaries_summary_node", "generate_parties_summary_node"
    ]
    for node_name in end_nodes:
        workflow.add_edge(node_name, END)
    logger.info("Grafo de LangGraph construido.")
    return workflow
