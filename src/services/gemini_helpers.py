"""
Este módulo proporciona funciones de ayuda para interactuar con la API
de Google Gemini. Incluye configuración, obtención de modelos y métodos
para generar contenido en modo streaming y no-streaming, así como para
parsear JSON de las respuestas del modelo.
"""
import logging
import json
import os
import re
from typing import Iterable, Union, Any
import google.generativeai as genai
from opik import track
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)


def configure_gemini(api_key: str):
    """Configura la API de Gemini."""
    if not api_key:
        raise ValueError("API key for Gemini is required and was not provided.")
    genai.configure(api_key=api_key)


def get_gemini_model(model_name: str = None) -> genai.GenerativeModel:
    """Obtiene una instancia del modelo generativo de Gemini."""
    model_name = model_name or os.environ.get(
        'GEMINI_MODEL', 'gemini-2.5-flash-preview-05-20'
    )
    return genai.GenerativeModel(model_name)

@track
def decode_gemini_stream(
    prompt_text: Union[str, list],
    stream_response_iterable: Iterable[genai.types.GenerateContentResponse]
) -> Iterable[str]:
    """
    Decodifica un stream de Gemini y produce los chunks de texto.
    """
    logger.info("Question: %s", str(prompt_text))
    final_response = ''
    for response_chunk in stream_response_iterable:
        try:
            if response_chunk.candidates:
                candidate = response_chunk.candidates[0]
                if candidate.content and candidate.content.parts:
                    text_part = candidate.content.parts[0].text
                    if text_part:
                        final_response += text_part
                        yield text_part
                else:
                    logger.info("Chunk sin 'parts', posiblemente final del stream.")
            else:
                logger.info("Sin candidatos en el chunk del stream.")
        except StopIteration:
            logger.info("StopIteration encontrada, finalizando stream.")
            break
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error(
                "Error procesando chunk de Gemini en decode_gemini_stream: %s",
                e, exc_info=True
            )
    return final_response


def generate_content_stream(
    model: genai.GenerativeModel, prompt_text: Union[str, list]
) -> Iterable[str]:
    """Genera contenido como un stream (generador)."""
    try:
        response_iterable = model.generate_content(prompt_text, stream=True)
        yield from decode_gemini_stream(prompt_text, response_iterable)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error(
            "Error crítico al generar contenido STREAM con Gemini (Prompt: '%s...'): %s",
            str(prompt_text)[:100], str(e), exc_info=True
        )
        yield f"Error al generar contenido con el modelo (stream): {str(e)}"


def generate_content_non_stream(
    model: genai.GenerativeModel, prompt_text: Union[str, list]
) -> str:
    """
    Genera contenido como una cadena de texto completa (no stream).
    """
    try:
        response = model.generate_content(prompt_text, stream=False)
        text_result = None
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                text_result = candidate.content.parts[0].text

        if text_result is None and hasattr(response, 'text') and response.text:
            logger.warning(
                "Usando atributo .text de fallback para extraer texto de respuesta."
            )
            text_result = response.text

        if text_result is not None:
            return str(text_result)

        logger.error(
            "No se pudo extraer texto de la respuesta NO-STREAM de Gemini. "
            "Prompt: '%s...'. Respuesta: %s...",
            str(prompt_text)[:100], str(response)[:500]
        )
        return "ERROR_NO_TEXT_EXTRACTED_FROM_GEMINI_NON_STREAM"

    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error(
            "Error crítico en API NON-STREAM de Gemini (Prompt: '%s...'): %s",
            str(prompt_text)[:100], str(e), exc_info=True
        )
        return f"ERROR_GEMINI_API_CALL_FAILED_NON_STREAM: {str(e)}"


def _extract_json_str(text: str) -> Union[str, None]:
    """
    Función auxiliar que extrae una cadena con formato JSON del texto.
    """
    # Expresión regular para encontrar un bloque de código JSON o un JSON "desnudo"
    pattern = r'```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        # El primer grupo captura el JSON dentro de ```json ... ```
        # El segundo grupo captura el JSON "desnudo"
        return match.group(1) if match.group(1) else match.group(2)
    return None


def parse_json_from_text(text: str, default_if_error: Any = None) -> Any:
    """
    Extrae un objeto JSON de una cadena de texto.
    """
    if not text or text.startswith("ERROR_"):
        logger.error(
            "No se intentará parsear JSON por error previo: %s", text
        )
        return default_if_error

    try:
        json_str = _extract_json_str(text)
        if not json_str:
            logger.warning(
                "No se encontró un JSON válido en el texto: '%s...'", text[:500]
            )
            return default_if_error
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = json_str[start:end+1]
                return json.loads(json_str)
            # pylint: disable=raise-missing-from
            raise json.JSONDecodeError(
                "No se pudo delimitar un objeto JSON claro.", json_str, 0
            )

    except json.JSONDecodeError as e:
        logger.error("Error al decodificar JSON: %s. Texto (parcial): '%s...'",
                     str(e), text[:500])
        return default_if_error
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Error inesperado al parsear JSON: %s. Texto: '%s...'",
                     str(e), text[:500])
        return default_if_error
