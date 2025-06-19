"""
Módulo principal de la aplicación Flask para gestionar
"""
from collections.abc import Iterable
import logging
import os
import sys
import uuid

from dotenv import load_dotenv
from flask import (Flask, Response, g, jsonify, render_template, request,
                   stream_with_context)

# Añadir el directorio raíz del proyecto al sys.path
# para que los módulos de 'src' puedan ser importados correctamente.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# pylint: disable=import-error,wrong-import-position
from src.services.gemini_helpers import configure_gemini
from src.services.infosubvenciones_service import info_subvenciones_service
from src.services.langgraph_service import LangGraphService

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Configuración del logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Inicialización de servicios
gemini_api_key = os.getenv('GEMINI_API_KEY')
langgraph_agent_instance = None

if gemini_api_key:
    try:
        # Configurar Gemini globalmente una sola vez
        configure_gemini(api_key=gemini_api_key)
        langgraph_agent_instance = LangGraphService(api_key=gemini_api_key)
        app.logger.info("LangGraphAgent inicializado correctamente.")
    except IndexError as e:
        app.logger.error("Error al inicializar LangGraphAgent: %s", e, exc_info=True)
else:
    app.logger.warning(
        "GEMINI_API_KEY no encontrada. El servicio de chat no estará disponible."
    )

# Almacenamiento en memoria para los historiales de chat
chat_histories = {}


@app.before_request
def before_request_func():
    """
    Función que se ejecuta antes de cada petición.
    Actualmente no realiza ninguna acción principal, pero está preparada
    para gestionar un 'thread_id' de chat si fuera necesario.
    """
    if 'chat_thread_id' not in g:
        # Se podría usar la sesión de Flask para persistir el thread_id,
        # pero actualmente el cliente genera y envía su propio ID.
        pass


@app.route('/')
def index():
    """Renderiza la página principal de la aplicación."""
    return render_template('index.html')


@app.route('/api/buscar', methods=['GET'])
def buscar_convocatorias_api():
    """API endpoint para buscar convocatorias de subvenciones."""
    # '1': todas las palabras, '2': cualquiera, '0': frase exacta
    descripcion_tipo_busqueda = request.args.get('descripcionTipoBusqueda', '1')
    params = {
        'page': request.args.get('page', '0'),
        'pageSize': request.args.get('pageSize', '1000'),
        'descripcion': request.args.get('descripcion', ''),
        'descripcionTipoBusqueda': descripcion_tipo_busqueda,
        'fechaDesde': request.args.get('fechaDesde', ''),  # DD/MM/YYYY
        'fechaHasta': request.args.get('fechaHasta', ''),  # DD/MM/YYYY
        'tipoAdministracion': request.args.get('tipoAdministracion', '')
    }
    # Eliminar parámetros vacíos para no enviarlos a la API externa
    params = {k: v for k, v in params.items() if v}
    try:
        resultados = info_subvenciones_service.buscar_convocatorias(params)
        return jsonify(resultados)
    except IndexError as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/convocatoria/<id_conv>', methods=['GET'])
def obtener_convocatoria_api(id_conv):
    """API endpoint para obtener el detalle de una convocatoria específica."""
    try:
        convocatoria = info_subvenciones_service.obtener_convocatoria(id_conv)
        return jsonify(convocatoria)
    except IndexError as e:
        app.logger.error("Error en /api/convocatoria/%s: %s", id_conv, e)
        return jsonify({'error': str(e)}), 500


def _update_chat_history(thread_id, query, response):
    """Función auxiliar para actualizar el historial de chat."""
    if not response or not response.strip():
        return  # No actualizar si la respuesta está vacía

    new_entry = (query, response.strip())
    history = chat_histories.get(thread_id, [])
    history.append(new_entry)

    max_history_length = 10  # Últimas 5 interacciones (5 pares)
    chat_histories[thread_id] = history[-max_history_length:]


@app.route('/api/chat', methods=['POST'])
def procesar_chat():
    """
    Procesa una consulta de chat, interactúa con el agente de LangGraph
    y devuelve una respuesta, potencialmente como un stream.
    """
    if not langgraph_agent_instance:
        return Response(
            "El servicio de chat inteligente no está disponible.",
            mimetype='text/plain', status=503
        )

    try:
        data = request.json
        consulta = data.get('consulta', '')
        client_thread_id = data.get('thread_id') or str(uuid.uuid4())

        if client_thread_id not in chat_histories:
            chat_histories[client_thread_id] = []

        if not consulta:
            return Response("La consulta es obligatoria", mimetype='text/plain', status=400)

        current_chat_history = chat_histories.get(client_thread_id, [])
        ai_response = langgraph_agent_instance.process_chat_query(
            consulta, current_chat_history, client_thread_id
        )

        # Caso 1: La respuesta es un stream (generador)
        if isinstance(ai_response, Iterable) and not isinstance(ai_response, str):
            app.logger.info(
                "Respuesta en modo stream para la consulta: '%s' (Thread: %s)",
                consulta, client_thread_id
            )

            def generate_and_accumulate_stream():
                full_response_chunks = []
                try:
                    for chunk in ai_response:
                        full_response_chunks.append(chunk)
                        yield chunk
                except IndexError as e:
                    app.logger.error("Error durante el streaming: %s", e, exc_info=True)
                    yield " Lo siento, ha ocurrido un error al generar la respuesta."
                finally:
                    accumulated = "".join(full_response_chunks)
                    _update_chat_history(client_thread_id, consulta, accumulated)

            return Response(
                stream_with_context(generate_and_accumulate_stream()),
                mimetype='text/plain; charset=utf-8'
            )

        # Caso 2: La respuesta es una cadena de texto normal
        if isinstance(ai_response, str):
            _update_chat_history(client_thread_id, consulta, ai_response)
            if not ai_response.strip():
                log_msg = (
                    "LangGraph devolvió una respuesta vacía (no-stream) para "
                    f"la consulta: '{consulta}' (Thread: {client_thread_id})."
                )
                app.logger.warning(log_msg)
                ai_response = "No se pudo generar una respuesta. Inténtalo de nuevo."
            return Response(ai_response, mimetype='text/plain; charset=utf-8')

        # Caso 3: Tipo de respuesta inesperado
        log_msg = (
            f"Tipo de respuesta inesperado de LangGraph: {type(ai_response)} "
            f"para la consulta: '{consulta}' (Thread: {client_thread_id})"
        )
        app.logger.error(log_msg)
        return Response(
            "Error: Tipo de respuesta inesperado del servicio de IA.",
            mimetype='text/plain', status=500
        )

    except IndexError as e:
        app.logger.error("Error crítico en /api/chat: %s", e, exc_info=True)
        error_response = (
            "Ocurrió un error interno al procesar tu consulta. "
            "Por favor, inténtalo de nuevo más tarde."
        )
        return Response(error_response, mimetype='text/plain', status=500)


if __name__ == '__main__':
    # El modo debug de Flask no es recomendable para producción debido al
    # reinicio automático, que puede afectar a estados en memoria.
    # Para producción, se recomienda usar un servidor WSGI como Gunicorn.
    FLASK_DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT, debug=FLASK_DEBUG_MODE)
