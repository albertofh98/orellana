# src/services/langgraph_service.py
import logging
import os
from typing import List, Tuple, Optional, Any
from langgraph.checkpoint.memory import MemorySaver
from src.services.graph_state import GraphState
from src.services.infosubvenciones_service import info_subvenciones_service
from src.services.gemini_helpers import (get_gemini_model,
                                         generate_content_non_stream,
                                         generate_content_stream)
from src.agents.extractor_agent import ExtractorAgent
from src.agents.api_caller_agent import ApiCallerAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.error_handler_agent import ErrorHandlerAgent
from src.agents.beneficiaries_agent import BeneficiariesAgent
from src.agents.political_parties_agent import PoliticalPartiesAgent
from src.graph.graph import build_agent_graph

logger = logging.getLogger(__name__)


class LangGraphService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required.")

        # Asegúrate de que GEMINI_MODEL esté en tus variables de entorno o cámbialo aquí
        self._model = get_gemini_model(os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash-latest'))
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
        # NOTA: Nombres de archivo deben coincidir con los archivos en prompts/
        # Y las claves usadas aquí deben coincidir con las usadas en los agentes
        prompt_files = {
            "orchestrator": "orchestrator_prompt.txt",
            "convocatoria_extractor": "convocatoria_extractor_prompt.txt",
            "extract_params": "extract_params_prompt.txt",
            "generate_detailed_response": "generate_detailed_response_prompt.txt",
            "generate_search_summary": "generate_search_summary_prompt.txt",
            "generate_general_response": "generate_general_response_prompt.txt",
            "extract_years": "extract_years_prompt.txt",
            "generate_beneficiaries_summary": "generate_beneficiaries_summary_prompt.txt",
            "extract_party_params": "extract_party_params_prompt.txt",
            "generate_parties_summary": "generate_parties_summary_prompt.txt"
        }
        loaded_prompts = {}
        for name, fname in prompt_files.items():
            try:
                with open(os.path.join(prompt_dir, fname), 'r', encoding='utf-8') as f:
                    loaded_prompts[name] = f.read()
            except FileNotFoundError:
                loaded_prompts[name] = f"ERROR: Prompt '{name}' ({fname}) not found."
        return loaded_prompts

    def _format_chat_history(self, chat_history: List[Tuple[str, str]]) -> str:
        if not chat_history:
            return "No previous chat history."
        return "\n".join([f"User: {q}\nAssistant: {a}" for q, a in chat_history])

    # Helper para generación NO-STREAM (usado por GeneratorAgent para respuestas simples o errores)
    def _call_llm_for_generation_non_stream(self, model, prompt: str, node_name: str) -> Tuple[str, bool, Optional[str]]:
        full_response = generate_content_non_stream(model, prompt)
        if "ERROR_" in full_response or not full_response.strip():
            error_msg = f"Invalid response from model (non-stream) for {node_name}: {full_response}"
            logger.warning(error_msg)
            return "I'm sorry, there was an issue generating the response.", False, error_msg
        return full_response.strip(), True, None

    # Helper para generación STREAM (usado por LangGraphService directamente)
    def _call_llm_for_generation_stream(self, prompt: str, node_name: str):
        logger.info(f"Initiating LLM stream for node {node_name} with prompt: {prompt[:100]}...")
        yield from generate_content_stream(self._model, prompt)

    def process_chat_query(self, query: str,
                           chat_history: List[Tuple[str, str]],
                           thread_id: str) -> Any:
        logger.info(f"Processing query: '{query}', Thread ID: {thread_id}")
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
        # Validar que todos los campos de GraphState están presentes en initial_state_dict
        # Esto es más para desarrollo y depuración.
        for key in GraphState.__annotations__.keys():
            if key not in initial_state_dict:
                logger.warning(f"GraphState key '{key}' missing in initial_state_dict for process_chat_query. Setting to None.")
                initial_state_dict[key] = None

        config = {"configurable": {"thread_id": thread_id}}

        # El grafo se ejecuta. Los nodos generadores ahora ponen 'stream_generation_prompt'.
        # El estado devuelto por invoke() SÍ será serializado por MemorySaver.
        # Como 'stream_generation_prompt' es un string, no habrá error de serialización.
        final_state = self.app.invoke(initial_state_dict, config=config)
        logger.debug(f"Final state from graph invoke for thread '{thread_id}': {final_state}")
        # Ahora, DESPUÉS de que el grafo haya terminado y
        # el checkpoint (si ocurre) se haya realizado,
        # verificamos si necesitamos generar un stream.
        if final_state.get("stream_generation_prompt"):
            prompt_for_stream = final_state["stream_generation_prompt"]
            node_name_for_stream = final_state.get("stream_generation_node_name",
                                                   "unknown_stream_node")
            # Devolvemos el generador que Flask consumirá.
            return self._call_llm_for_generation_stream(prompt_for_stream, node_name_for_stream)
        elif final_state.get("agent_response_text"):
            logger.info("Returning non-stream text response from final_state.")
            return final_state["agent_response_text"]
        elif final_state.get("error_message"):
            return final_state.get("agent_response_text") or "An error occurred."
        else:
            logger.error("""Graph execution finished but no stream prompt,
                            response text, or error message found in final state.""")
        return "I'm sorry, I couldn't process your request adequately."
