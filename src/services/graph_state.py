from typing import TypedDict, Optional, Any, List, Tuple


class GraphState(TypedDict):
    original_query: str
    chat_history: List[Tuple[str, str]]
    formatted_chat_history: str
    intent: Optional[str]
    extracted_convocatoria_id: Optional[str]
    extracted_years: Optional[str]
    api_call_params: Optional[dict]
    api_response_data: Optional[Any]
    error_message: Optional[str]
    last_stream_event_node: Optional[str]
    stream_completed_successfully: Optional[bool]
    agent_response_text: Optional[str]
    stream_generation_prompt: Optional[str]
    stream_generation_node_name: Optional[str]
