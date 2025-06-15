# src/agents/beneficiaries_agent.py
import logging
import json # Para el log final
from src.services.graph_state import GraphState
from src.services.infosubvenciones_service import info_subvenciones_service

logger = logging.getLogger(__name__)

class BeneficiariesAgent:
    def __init__(self):
        self.infosubvenciones_service = info_subvenciones_service

    def get_beneficiaries_by_year(self, state: GraphState) -> dict:
        node_name = "get_beneficiaries_node"
        extracted_years_str = state.get("extracted_years")
        
        logger.info(f"Nodo: {node_name}, Años extraídos (string) del estado: '{extracted_years_str}'")

        if not extracted_years_str:
            logger.warning(f"{node_name}: No se proporcionaron años para la búsqueda.")
            return {
                "api_response_data": {},
                "error_message": "No se proporcionaron años válidos para la búsqueda.",
                "last_stream_event_node": node_name
            }

        try:
            target_years_int_list = [int(year.strip()) for year in extracted_years_str.split(',') if year.strip().isdigit()]
            if not target_years_int_list:
                raise ValueError("La cadena de años procesada no resultó en una lista válida de enteros.")
        except ValueError as ve:
            logger.error(f"{node_name}: Error al convertir años a enteros: '{extracted_years_str}'. Error: {ve}")
            return {
                "api_response_data": {},
                "error_message": f"Formato de años inválido: '{extracted_years_str}'. Use comas para separar años (ej: 2022,2023).",
                "last_stream_event_node": node_name
            }

        logger.info(f"{node_name}: Años a consultar en la API (lista de enteros): {target_years_int_list}")
        
        structured_api_data_for_prompt = {}
        errors_occurred = []

        try:
            logger.info(f"{node_name}: Llamando a infosubvenciones_service.obtener_beneficiarios_por_anno con años: {target_years_int_list}")
            api_response_object = self.infosubvenciones_service.obtener_beneficiarios_por_anno(target_years_int_list)
            
            # Loguear solo una parte si es muy grande, o usar json.dumps para mejor formato si es necesario.
            logger.info(f"{node_name}: Respuesta CRUDA de la API (tipo: {type(api_response_object)}): {str(api_response_object)[:1000]}") # Aumentado a 1000 chars

            # Inicializa la estructura de datos para cada año solicitado
            for year_val in target_years_int_list:
                structured_api_data_for_prompt[year_val] = []

            # --- NUEVA LÓGICA DE PROCESAMIENTO DE API ---
            if isinstance(api_response_object, dict) and 'content' in api_response_object:
                beneficiaries_list_from_api = api_response_object['content']
                if isinstance(beneficiaries_list_from_api, list):
                    if not beneficiaries_list_from_api:
                        logger.info(f"{node_name}: La API devolvió una lista 'content' vacía para los años {target_years_int_list}.")
                    
                    for beneficiary_item in beneficiaries_list_from_api:
                        # ** IMPORTANTE: Asegúrate de que 'ejercicio' es el nombre correcto del campo de año. **
                        # Basado en tu log: {'idPersona': ..., 'beneficiario': ..., 'ejercicio': 2023, ...}
                        # 'ejercicio' parece ser el campo correcto.
                        item_year_field = beneficiary_item.get('ejercicio') 
                        
                        if item_year_field is None:
                            logger.warning(f"{node_name}: Beneficiario en 'content' sin campo 'ejercicio': {str(beneficiary_item)[:100]}")
                            continue

                        try:
                            item_year_int = int(item_year_field)
                            if item_year_int in structured_api_data_for_prompt:
                                # Asegurarse de que sigue siendo una lista (debería serlo por la inicialización)
                                if not isinstance(structured_api_data_for_prompt[item_year_int], list):
                                     structured_api_data_for_prompt[item_year_int] = [] # Re-inicializar por si acaso
                                structured_api_data_for_prompt[item_year_int].append(beneficiary_item)
                            else:
                                logger.warning(f"{node_name}: API devolvió en 'content' datos para el año {item_year_int} que no fue solicitado o no está en target_years_int_list. Datos: {beneficiary_item}")
                        except ValueError:
                            logger.warning(f"{node_name}: Valor de 'ejercicio' no entero ('{item_year_field}') en item de beneficiario: {beneficiary_item}")
                else:
                    logger.warning(f"{node_name}: La clave 'content' en la respuesta de la API no es una lista. Tipo: {type(beneficiaries_list_from_api)}")
            elif isinstance(api_response_object, list): # Si la API devolviera directamente una lista (menos probable según tu log)
                logger.info(f"{node_name}: La API devolvió directamente una lista. Procesando como lista plana...")
                # Aquí aplicarías la lógica de la "Suposición 1" de la versión anterior si fuera necesario.
                # Por ahora, nos centramos en la estructura de 'content'.
                for beneficiary_item in api_response_object:
                    item_year_field = beneficiary_item.get('ejercicio')
                    if item_year_field is not None:
                        try:
                            item_year_int = int(item_year_field)
                            if item_year_int in structured_api_data_for_prompt:
                                if not isinstance(structured_api_data_for_prompt[item_year_int], list):
                                     structured_api_data_for_prompt[item_year_int] = []
                                structured_api_data_for_prompt[item_year_int].append(beneficiary_item)
                        except ValueError:
                             logger.warning(f"{node_name}: Valor de 'ejercicio' no entero ('{item_year_field}') en item de beneficiario (lista directa): {beneficiary_item}")
            else:
                logger.warning(f"{node_name}: Respuesta inesperada de la API. No es un diccionario con 'content' ni una lista. Se asumirá que no hay datos. Tipo: {type(api_response_object)}")
            # --- FIN NUEVA LÓGICA ---

            # Para los años que no obtuvieron datos (la lista sigue vacía), establece el mensaje.
            for year_val in target_years_int_list:
                # Comprobar si existe la clave y si es una lista vacía
                current_data_for_year = structured_api_data_for_prompt.get(year_val)
                if isinstance(current_data_for_year, list) and not current_data_for_year:
                    structured_api_data_for_prompt[year_val] = f"Para el año {year_val}, no se encontraron datos de beneficiarios."
                elif current_data_for_year is None: # Si el año nunca se procesó o se eliminó la clave
                     structured_api_data_for_prompt[year_val] = f"No se pudo obtener información de beneficiarios para el año {year_val} (datos no presentes después del procesamiento)."


        except Exception as e:
            error_msg_api = f"Error crítico al llamar o procesar la API de beneficiarios para los años {target_years_int_list}: {e}"
            logger.error(error_msg_api, exc_info=True)
            errors_occurred.append(error_msg_api)
            for year_val in target_years_int_list:
                structured_api_data_for_prompt[year_val] = f"Error al obtener datos de beneficiarios para el año {year_val} debido a un problema con la API."
        
        final_error_to_propagate_to_state = state.get("error_message") or (errors_occurred[0] if errors_occurred else None)
        
        # Usar json.dumps para el log para mejor legibilidad de estructuras complejas
        logger.info(f"{node_name}: Datos estructurados que se pasarán al generador (api_response_data): {json.dumps(structured_api_data_for_prompt, ensure_ascii=False, indent=2)}")
        
        return {
            "api_response_data": structured_api_data_for_prompt, 
            "error_message": final_error_to_propagate_to_state,
            "last_stream_event_node": node_name
        }