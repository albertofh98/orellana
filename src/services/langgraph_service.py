"""
Este módulo define el LangGraphService, que orquesta la lógica del chatbot.

Inicializa los agentes, construye el grafo de LangGraph y procesa las
consultas del usuario, gestionando el estado y el flujo de ejecución.
"""
import logging
import os
from typing import List, Tuple, Optional, Any
from langgraph.checkpoint.memory import MemorySaver
from agents.extractor_agent import ExtractorAgent
from agents.api_caller_agent import ApiCallerAgent
from agents.generator_agent import GeneratorAgent
from agents.error_handler_agent import ErrorHandlerAgent
from agents.beneficiaries_agent import BeneficiariesAgent
from agents.political_parties_agent import PoliticalPartiesAgent
from graph.graph import build_agent_graph
from .graph_state import GraphState
from .infosubvenciones_service import info_subvenciones_service
from .gemini_helpers import (get_gemini_model,
                           generate_content_non_stream,
                           generate_content_stream)
import opik

logger = logging.getLogger(__name__)
opik.configure(use_local=False)
opik_client = opik.Opik()
os.environ["OPIK_PROJECT_NAME"] = "orellana"


# pylint: disable=too-few-public-methods
class LangGraphService:
    """
    Servicio que encapsula la lógica del grafo de agentes de LangGraph.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required.")

        model_name = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash-latest')
        self._model = get_gemini_model(model_name)
        prompts = self._load_prompts()
        agents = {
            "extractor": ExtractorAgent(self._model, {
                "orchestrator": prompts["orchestrator"],
                "extractor": prompts["convocatoria_extractor"],
                "search_params": prompts["extract_params"],
                "extract_years": prompts["extract_years"],
                "extract_party_params": prompts["extract_party_params"]
            }),
            "api_caller": ApiCallerAgent(info_subvenciones_service),
            "generator": GeneratorAgent(
                self._model,
                {
                    "detailed_response": prompts["generate_detailed_response"],
                    "search_summary": prompts["generate_search_summary"],
                    "general_response": prompts["generate_general_response"],
                    "beneficiaries_summary": prompts["generate_beneficiaries_summary"],
                    "parties_summary": prompts["generate_parties_summary"]
                },
                llm_helper_non_stream=self._call_llm_for_generation_non_stream,
                llm_helper_stream=self._call_llm_for_generation_stream
            ),
            "beneficiaries": BeneficiariesAgent(),
            "political_parties": PoliticalPartiesAgent(),
            "error_handler": ErrorHandlerAgent()
        }

        graph = build_agent_graph(agents)
        self.memory = MemorySaver()
        self.app = graph.compile(checkpointer=self.memory)
        logger.info("LangGraphService initialized: compiled graph + MemorySaver.")

    def _load_prompts(self) -> dict:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_dir = os.path.join(base_dir, '../../prompts/')
        prompt_files = {
            "orchestrator":"orchestrator_prompt",
            "convocatoria_extractor": "convocatoria_extractor_prompt",
            "extract_params": "extract_params_prompt",
            "generate_detailed_response": "generate_detailed_response_prompt",
            "generate_search_summary": "generate_search_summary_prompt",
            "generate_general_response": "generate_general_response_prompt",
            "extract_years": "extract_years_prompt",
            "generate_beneficiaries_summary":
                "generate_beneficiaries_summary_prompt",
            "extract_party_params": "extract_party_params_prompt",
            "generate_parties_summary": "generate_parties_summary_prompt"
        }
        loaded_prompts = {}
        for name, fname in prompt_files.items():
            try:
                loaded_prompts[name] = opik_client.get_prompt(name=fname).prompt
            except FileNotFoundError:
                error_msg = f"ERROR: Prompt '{name}' ({fname}) not found."
                loaded_prompts[name] = error_msg
        return loaded_prompts

    def _format_chat_history(self, chat_history: List[Tuple[str, str]]) -> str:
        if not chat_history:
            return "No previous chat history."
        return "\n".join([f"User: {q}\nAssistant: {a}" for q, a in chat_history])

    def _call_llm_for_generation_non_stream(
        self, model, prompt: str, node_name: str
    ) -> Tuple[str, bool, Optional[str]]:
        """Genera una respuesta no-stream y maneja errores."""
        full_response = generate_content_non_stream(model, prompt)
        if "ERROR_" in full_response or not full_response.strip():
            error_msg = (f"Invalid response from model (non-stream) for "
                         f"{node_name}: {full_response}")
            logger.warning(error_msg)
            err_text = "I'm sorry, there was an issue generating the response."
            return err_text, False, error_msg
        return full_response.strip(), True, None

    def _call_llm_for_generation_stream(self, prompt: str, node_name: str):
        """Genera una respuesta en modo stream."""
        logger.info("Initiating LLM stream for node %s with prompt: %s...",
                     node_name, prompt[:100])
        yield from generate_content_stream(self._model, prompt)

    def process_chat_query(self, query: str,
                           chat_history: List[Tuple[str, str]],
                           thread_id: str) -> Any:
        """Procesa una consulta de chat, ejecuta el grafo y devuelve la respuesta."""
        logger.info("Processing query: '%s', Thread ID: %s", query, thread_id)
        initial_state_dict = {
            "original_query": query,
            "chat_history": chat_history,
            "formatted_chat_history": self._format_chat_history(chat_history),
            "intent": None,
            "extracted_convocatoria_id": None,
            "extracted_years": None,
            "api_call_params": None,
            "api_response_data": None,
            "error_message": None,
            "last_stream_event_node": None,
            "stream_completed_successfully": None,
            "agent_response_text": None,
            "stream_generation_prompt": None,
            "stream_generation_node_name": None
        }
        for key in GraphState.__annotations__.keys():
            if key not in initial_state_dict:
                logger.warning(
                    "GraphState key '%s' missing in initial_state_dict. "
                    "Setting to None.", key
                )
                initial_state_dict[key] = None

        config = {"configurable": {"thread_id": thread_id}}

        final_state = self.app.invoke(initial_state_dict, config=config)
        logger.debug("Final state from graph invoke for thread '%s': %s",
                     thread_id, final_state)

        if final_state.get("stream_generation_prompt"):
            prompt_stream = final_state["stream_generation_prompt"]
            node_name = final_state.get("stream_generation_node_name", "unknown")
            return self._call_llm_for_generation_stream(prompt_stream, node_name)

        if final_state.get("agent_response_text"):
            logger.info("Returning non-stream text response from final_state.")
            return final_state["agent_response_text"]

        if final_state.get("error_message"):
            return final_state.get("agent_response_text") or "An error occurred."

        logger.error("Graph finished but no response text or error message found.")
        return "I'm sorry, I couldn't process your request adequately."
