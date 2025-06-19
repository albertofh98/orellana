import logging
import json
from src.services.graph_state import GraphState
from src.services.infosubvenciones_service import info_subvenciones_service


logger = logging.getLogger(__name__)


class BeneficiariesAgent:
    def __init__(self):
        self.infosubvenciones_service = info_subvenciones_service

    def get_beneficiaries_by_year(self, state: GraphState) -> dict:
        node_name = "get_beneficiaries_node"
        extracted_years_str = state.get("extracted_years")
        logger.info(
            f"Nodo: {node_name}, Años extraídos (string) del estado: "
            f"'{extracted_years_str}'"
        )

        if not extracted_years_str:
            logger.warning(
                f"{node_name}: No se proporcionaron años para la búsqueda."
            )
            return {
                "api_response_data": {},
                "error_message": "No se proporcionaron años válidos para la búsqueda.",
                "last_stream_event_node": node_name
            }

        try:
            target_years_int_list = [
                int(year.strip()) for year in extracted_years_str.split(',')
                if year.strip().isdigit()
            ]
            if not target_years_int_list:
                msg = "La cadena de años procesada no resultó en una lista válida."
                raise ValueError(msg)
        except ValueError:
            return {
                "api_response_data": {},
                "error_message": (
                    f"Formato de años inválido: '{extracted_years_str}'. "
                    "Use comas para separar años (ej: 2022,2023)."
                ),
                "last_stream_event_node": node_name
            }

        logger.info(
            f"{node_name}: Años a consultar en la API (lista de enteros): "
            f"{target_years_int_list}"
        )
        structured_api_data_for_prompt = {}
        errors_occurred = []

        try:
            logger.info(
                f"{node_name}: Llamando a "
                "infosubvenciones_service.obtener_beneficiarios_por_anno "
                f"con años: {target_years_int_list}"
            )
            api_response_object = (
                self.infosubvenciones_service.obtener_beneficiarios_por_anno(
                    target_years_int_list
                )
            )
            logger.info(
                f"{node_name}: Respuesta CRUDA de la API "
                f"(tipo: {type(api_response_object)}): "
                f"{str(api_response_object)[:1000]}"
            )

            for year_val in target_years_int_list:
                structured_api_data_for_prompt[year_val] = []

            if isinstance(api_response_object, dict) and 'content' in api_response_object:
                beneficiaries_list_from_api = api_response_object['content']
                if isinstance(beneficiaries_list_from_api, list):
                    if not beneficiaries_list_from_api:
                        logger.info(
                            f"{node_name}: La API devolvió una lista 'content' "
                            f"vacía para los años {target_years_int_list}."
                        )

                    for beneficiary_item in beneficiaries_list_from_api:
                        # IMPORTANTE: Asegúrate de que 'ejercicio' es el nombre
                        # correcto del campo de año. Basado en tu log:
                        # {'idPersona': ..., 'beneficiario': ..., 'ejercicio': 2023, ...}
                        # 'ejercicio' parece ser el campo correcto.
                        item_year_field = beneficiary_item.get('ejercicio')

                        if item_year_field is None:
                            logger.warning(
                                f"{node_name}: Beneficiario en 'content' sin "
                                f"campo 'ejercicio': {str(beneficiary_item)[:100]}"
                            )
                            continue

                        try:
                            item_year_int = int(item_year_field)
                            if item_year_int in structured_api_data_for_prompt:
                                if not isinstance(
                                    structured_api_data_for_prompt[item_year_int], list
                                ):
                                    # Re-inicializar por si acaso
                                    structured_api_data_for_prompt[item_year_int] = []
                                structured_api_data_for_prompt[item_year_int].append(
                                    beneficiary_item
                                )
                            else:
                                logger.warning(
                                    f"{node_name}: API devolvió en 'content' datos para "
                                    f"el año {item_year_int} no solicitado. "
                                    f"Datos: {beneficiary_item}"
                                )
                        except ValueError:
                            logger.warning(
                                f"{node_name}: Valor de 'ejercicio' no entero "
                                f"('{item_year_field}') en item: {beneficiary_item}"
                            )
                else:
                    logger.warning(
                        f"{node_name}: La clave 'content' en la respuesta de la "
                        f"API no es una lista. Tipo: {type(beneficiaries_list_from_api)}"
                    )
            elif isinstance(api_response_object, list):
                logger.info(
                    f"{node_name}: La API devolvió directamente una lista. "
                    "Procesando como lista plana..."
                )
                for beneficiary_item in api_response_object:
                    item_year_field = beneficiary_item.get('ejercicio')
                    if item_year_field is not None:
                        try:
                            item_year_int = int(item_year_field)
                            if item_year_int in structured_api_data_for_prompt:
                                if not isinstance(
                                    structured_api_data_for_prompt[item_year_int], list
                                ):
                                    structured_api_data_for_prompt[item_year_int] = []
                                structured_api_data_for_prompt[item_year_int].append(
                                    beneficiary_item
                                )
                        except ValueError:
                            logger.warning(
                                f"{node_name}: Valor de 'ejercicio' no entero "
                                f"('{item_year_field}') en item (lista directa): "
                                f"{beneficiary_item}"
                            )
            else:
                logger.warning(
                    f"{node_name}: Respuesta inesperada de la API. No es un "
                    f"diccionario con 'content' ni una lista. Se asumirá que no "
                    f"hay datos. Tipo: {type(api_response_object)}"
                )

            for year_val in target_years_int_list:
                current_data = structured_api_data_for_prompt.get(year_val)
                if isinstance(current_data, list) and not current_data:
                    structured_api_data_for_prompt[year_val] = (
                        f"Para el año {year_val}, no se encontraron datos de beneficiarios."
                    )
                elif current_data is None:
                    structured_api_data_for_prompt[year_val] = (
                        f"No se pudo obtener info de beneficiarios para el año "
                        f"{year_val} (datos no presentes)."
                    )

        except Exception as e:
            error_msg_api = (
                "Error crítico al llamar o procesar la API de beneficiarios para "
                f"los años {target_years_int_list}: {e}"
            )
            logger.error(error_msg_api, exc_info=True)
            errors_occurred.append(error_msg_api)
            for year_val in target_years_int_list:
                structured_api_data_for_prompt[year_val] = (
                    f"Error al obtener datos de beneficiarios para el año {year_val} "
                    "debido a un problema con la API."
                )

        final_error_to_propagate_to_state = state.get("error_message") or (
            errors_occurred[0] if errors_occurred else None
        )

        log_data = json.dumps(
            structured_api_data_for_prompt, ensure_ascii=False, indent=2
        )
        logger.info(
            f"{node_name}: Datos estructurados que se pasarán al generador "
            f"(api_response_data): {log_data}"
        )

        return {
            "api_response_data": structured_api_data_for_prompt,
            "error_message": final_error_to_propagate_to_state,
            "last_stream_event_node": node_name
        }
