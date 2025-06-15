import os
import sys
from flask import Flask, render_template, request, jsonify, Response, g, stream_with_context # Added stream_with_context
from dotenv import load_dotenv
import logging
import uuid # To generate conversation/thread IDs
from collections.abc import Iterable # To check if it's a generator

# Ensure the root directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import services
from src.services.gemini_helpers import configure_gemini # Import the configurator
from src.services.langgraph_service import LangGraphService # Import the new LangGraph agent
from src.services.infosubvenciones_service import info_subvenciones_service # Ensure it can be imported or pass the instance

app = Flask(__name__)

logging.basicConfig(level=logging.INFO) # logging.DEBUG for more detail
app.logger.setLevel(logging.INFO) # logging.DEBUG for more detail


gemini_api_key = os.getenv('GEMINI_API_KEY')
langgraph_agent_instance = None

if gemini_api_key:
    try:
        configure_gemini(api_key=gemini_api_key) # Configure Gemini globally once
        langgraph_agent_instance = LangGraphService(api_key=gemini_api_key)
        app.logger.info("LangGraphAgent initialized successfully.")
    except Exception as e:
        app.logger.error(f"Error initializing LangGraphAgent: {e}", exc_info=True)
else:
    app.logger.warning("GEMINI_API_KEY not found. The AI chat service will not be available.")

chat_histories = {} # In-memory storage for chat histories

@app.before_request
def before_request_func():
    # Try to get the thread_id from the session or headers if relevant to your flow
    # For now, we will rely on the thread_id sent in the JSON body for /api/chat
    # and will generate it in / if it doesn't exist for the page rendering session.
    # This `g.chat_thread_id` is mainly used if you need an ID *before* reaching the chat.
    if 'chat_thread_id' not in g:
        # This could be useful if a persistent thread_id through g and Flask sessions were needed
        # session_thread_id = session.get('chat_thread_id')
        # if not session_thread_id:
        #     session_thread_id = str(uuid.uuid4())
        #     session['chat_thread_id'] = session_thread_id
        # g.chat_thread_id = session_thread_id
        pass # We don't do anything with g.chat_thread_id here as the client sends its own ID


@app.route('/')
def index():
    # The JavaScript on the client will generate a thread_id if it doesn't exist
    # and send it with each chat request.
    return render_template('index.html')


@app.route('/api/buscar', methods=['GET'])
def buscar_convocatorias_api(): # Renamed to avoid conflict with imported function
    params = {
        'page': request.args.get('page', '0'),
        'pageSize': request.args.get('pageSize', '1000'),
        'descripcion': request.args.get('descripcion', ''),
        'descripcionTipoBusqueda': request.args.get('descripcionTipoBusqueda', '1'), # '1' for all words, '2' for any, '0' for exact phrase
        'fechaDesde': request.args.get('fechaDesde', ''), # DD/MM/YYYY
        'fechaHasta': request.args.get('fechaHasta', ''), # DD/MM/YYYY
        'tipoAdministracion': request.args.get('tipoAdministracion', '') # Administration type (e.g., State, Regional)
    }
    params = {k: v for k, v in params.items() if v} # Remove empty params
    
    try:
        # Assuming info_subvenciones_service is imported and available
        resultados = info_subvenciones_service.buscar_convocatorias(params)
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/convocatoria/<id_conv>', methods=['GET']) # Route parameter renamed in original file, kept for consistency
def obtener_convocatoria_api(id_conv): # Renamed to avoid conflict
    try:
        # Assuming info_subvenciones_service is imported and available
        convocatoria = info_subvenciones_service.obtener_convocatoria(id_conv)
        return jsonify(convocatoria)
    except Exception as e:
        app.logger.error(f"Error in /api/convocatoria/{id_conv}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def procesar_chat():
    if not langgraph_agent_instance:
        return Response("The intelligent chat service is not available.", mimetype='text/plain', status=503)
        
    try:
        data = request.json
        consulta = data.get('consulta', '') # User's query
        client_thread_id = data.get('thread_id') # Thread ID from the client

        if not client_thread_id: 
            client_thread_id = str(uuid.uuid4())
            # Ensure history is initialized for this new thread_id if it doesn't exist
            if client_thread_id not in chat_histories:
                 chat_histories[client_thread_id] = []
        
        # Retrieve history for this thread_id, or initialize if it's the first time for this ID
        current_chat_history = chat_histories.get(client_thread_id, [])
        if not current_chat_history and client_thread_id not in chat_histories : # Double check in case get returns default but it's not in dict
             chat_histories[client_thread_id] = [] # Ensure initialization
        
        if not consulta:
            return Response("Query is required", mimetype='text/plain', status=400)
        
        # Call the modified method that returns the full response or a stream
        ai_response_or_stream = langgraph_agent_instance.process_chat_query(consulta, current_chat_history, client_thread_id)
        
        if isinstance(ai_response_or_stream, Iterable) and not isinstance(ai_response_or_stream, str):
            # It's a generator/stream
            app.logger.info(f"Response is a stream for query: '{consulta}' (Thread: {client_thread_id})")
            
            # Function to consume the stream, send it to the client, and accumulate it for history
            def generate_and_accumulate_stream_response():
                full_ai_response_chunks = []
                try:
                    for chunk in ai_response_or_stream:
                        full_ai_response_chunks.append(chunk)
                        yield chunk
                except Exception as e:
                    app.logger.error(f"Error during streaming to client: {str(e)}", exc_info=True)
                    # Do not attempt to update history if the stream fails catastrophically
                    # The client may or may not receive this last chunk depending on where the error occurred.
                    yield " I'm sorry, an error occurred while generating the response. Please try again."
                    return # Do not proceed to update history if the stream had an error.
                finally:
                    # This block will execute even if there's a `return` in `try` or `except` if the stream was consumed
                    # (or attempted to be consumed).
                    # Only update history if the stream produced content.
                    accumulated_response = "".join(full_ai_response_chunks).strip()
                    if accumulated_response: # Only update if there's a non-empty accumulated response
                        new_history_entry = (consulta, accumulated_response) # Use the original query
                        
                        if client_thread_id not in chat_histories: # Double-check just in case
                            chat_histories[client_thread_id] = []
                        
                        updated_history_list = chat_histories[client_thread_id] + [new_history_entry]
                        
                        max_history_length = 10 # Example: last 5 interactions (5 pairs of query/response)
                        chat_histories[client_thread_id] = updated_history_list[-max_history_length:]
                    elif not full_ai_response_chunks: # If there were no chunks, meaning the stream was empty
                        app.logger.warning(f"LangGraphAgent returned an empty stream (post-stream) for: '{consulta}' (Thread: {client_thread_id}). History not updated.")
                    # If there were chunks but they resulted in an empty string after strip(), also log.
                    elif not accumulated_response and full_ai_response_chunks :
                         app.logger.warning(f"LangGraphAgent returned a stream that resulted in an empty response after strip() (post-stream) for: '{consulta}' (Thread: {client_thread_id}). History not updated.")


            return Response(stream_with_context(generate_and_accumulate_stream_response()), mimetype='text/plain; charset=utf-8')

        elif isinstance(ai_response_or_stream, str):
            # It's a normal text response (not a stream)
            ai_full_response = ai_response_or_stream
            
            # Update history AFTER the entire response has been generated
            if ai_full_response and ai_full_response.strip(): # Only add if there was a non-empty response
                new_history_entry = (consulta, ai_full_response.strip()) # Use the original query
                
                # Ensure history for the thread_id exists before trying to add to it
                if client_thread_id not in chat_histories: # Double check
                    chat_histories[client_thread_id] = []
                
                updated_history_list = chat_histories[client_thread_id] + [new_history_entry]
                
                max_history_length = 10
                chat_histories[client_thread_id] = updated_history_list[-max_history_length:]
            else:
                app.logger.warning(f"LangGraphAgent returned an empty or whitespace-only response (non-stream) for query: '{consulta}' (Thread: {client_thread_id}). History not updated with this entry.")
                if not ai_full_response: # If the response is None or completely empty, ensure the client receives something.
                    ai_full_response = "A response could not be generated at this time. Please try again."
            
            return Response(ai_full_response, mimetype='text/plain; charset=utf-8')
        else:
            # Unexpected case
            app.logger.error(f"Unexpected response type from LangGraphService: {type(ai_response_or_stream)} for query: '{consulta}' (Thread: {client_thread_id})")
            return Response("Error: Unexpected response type from AI service.", mimetype='text/plain; charset=utf-8', status=500)
        
    except Exception as e:
        app.logger.error(f"Critical error in /api/chat: {str(e)}", exc_info=True)
        # Ensure not to return internal error details to the client in production
        return Response("An internal error occurred while processing your query. Please try again later.", mimetype='text/plain; charset=utf-8', status=500)
    

if __name__ == '__main__':
    # Flask in debug mode is not recommended for production.
    # Automatic reloading can cause issues with in-memory states like chat_histories if not handled carefully.
    # For production, use a WSGI server like Gunicorn or uWSGI.
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)