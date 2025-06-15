import google.generativeai as genai
import logging
import json
import os
import re
from typing import Iterable, Union, Dict, Any

logger = logging.getLogger(__name__)

def configure_gemini(api_key: str):
    """Configura la API de Gemini."""
    if not api_key:
        raise ValueError("API key for Gemini is required and was not provided.")
    genai.configure(api_key=api_key)

def get_gemini_model(model_name: str = None) -> genai.GenerativeModel:
    """Obtiene una instancia del modelo generativo de Gemini."""
    model_name = model_name or os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-05-20')
    return genai.GenerativeModel(model_name)

def decode_gemini_stream(stream_response_iterable: Iterable[genai.types.GenerateContentResponse]) -> Iterable[str]:
    """
    Decodifica el stream de GenerateContentResponse de Gemini y produce los chunks de texto.
    """
    for response_chunk in stream_response_iterable:
        try:
            if response_chunk.candidates and len(response_chunk.candidates) > 0:
                candidate = response_chunk.candidates[0]
                if candidate.content and candidate.content.parts and len(candidate.content.parts) > 0:
                    text_part = candidate.content.parts[0].text
                    if text_part:
                        yield text_part
                else:
                    logger.info("decode_gemini_stream: Chunk sin parts, posiblemente final del stream.")
            else:
                logger.info("decode_gemini_stream: Sin candidatos en el chunk.")
        except StopIteration:
            logger.info("decode_gemini_stream: StopIteration encontrada, finalizando stream.")
            break
        except Exception as e:
            logger.error(f"Error procesando chunk de Gemini en decode_gemini_stream: {e}", exc_info=True)
            
def generate_content_stream(model: genai.GenerativeModel, prompt_text: Union[str, list]) -> Iterable[str]:
    """Genera contenido como un stream (generador)."""
    try:
        response_iterable = model.generate_content(prompt_text, stream=True)
        yield from decode_gemini_stream(response_iterable)
    except Exception as e:
        logger.error(f"Error crítico al generar contenido STREAM con Gemini (Prompt: '{str(prompt_text)[:100]}...'): {str(e)}", exc_info=True)
        yield f"Error al generar contenido con el modelo (stream): {str(e)}"

def generate_content_non_stream(model: genai.GenerativeModel, prompt_text: Union[str, list]) -> str:
    """
    Genera contenido como una cadena de texto completa (no stream).
    Asegura devolver siempre una cadena, incluso si es un mensaje de error.
    """
    try:
        response = model.generate_content(prompt_text, stream=False)
        text_result = None
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts and len(candidate.content.parts) > 0:
                text_result = candidate.content.parts[0].text

        if text_result is None and hasattr(response, 'text') and response.text:
            logger.warning("Extrayendo texto de respuesta no-stream usando el atributo .text de fallback (posiblemente porque part[0].text era None).")
            text_result = response.text

        if text_result is not None:
            return str(text_result)
        else:
            logger.error(f"No se pudo extraer texto significativo de la respuesta NO-STREAM de Gemini. Prompt: '{str(prompt_text)[:100]}...'. Respuesta Gemini: {str(response)[:500]}...")
            return "ERROR_NO_TEXT_EXTRACTED_FROM_GEMINI_NON_STREAM"

    except Exception as e:
        logger.error(f"Error crítico al generar contenido NON-STREAM con Gemini (Prompt: '{str(prompt_text)[:100]}...'): {str(e)}", exc_info=True)
        return f"ERROR_GEMINI_API_CALL_FAILED_NON_STREAM: {str(e)}"

def _extract_json_str(text: str) -> Union[str, None]:
    """
    Función auxiliar que extrae una cadena con formato JSON del texto.
    """
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})', text, re.DOTALL)
    if match:
        return match.group(1) if match.group(1) else match.group(2)
    return None

def parse_json_from_text(text: str, default_if_error: Any = None) -> Any:
    """
    Extrae un objeto JSON de una cadena de texto, buscando bloques de código JSON
    o JSON "desnudo".
    """
    if not text or text.startswith("ERROR_"):
        logger.error(f"No se intentará parsear JSON debido a un error previo en la generación de texto: {text}")
        return default_if_error
    try:
        json_str = _extract_json_str(text)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Intentar delimitar correctamente el objeto JSON
                start_brace = json_str.find('{')
                end_brace = json_str.rfind('}')
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_str = json_str[start_brace:end_brace+1]
                    return json.loads(json_str)
                else:
                    raise json.JSONDecodeError("No se pudo delimitar un objeto JSON claro.", json_str, 0)
        logger.warning(f"No se encontró un JSON válido en el texto (después del intento con regex): '{text[:500]}...'")
        return default_if_error
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON: {str(e)}. Texto problemático (parcial): '{text[:500]}...'")
        return default_if_error
    except Exception as e:
        logger.error(f"Error inesperado al parsear JSON: {str(e)}. Texto: '{text[:500]}...'")
        return default_if_error