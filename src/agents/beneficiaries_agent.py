"""
Módulo que define el agente encargado de obtener datos de beneficiarios de subvenciones.

Este agente se conecta con un servicio de información de subvenciones para recuperar
listas de beneficiarios basadas en uno o varios años proporcionados.
"""
import logging
import json
from typing import Any
from services.graph_state import GraphState
from services.infosubvenciones_service import info_subvenciones_service


logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class BeneficiariesAgent:
    """
    Agente para gestionar la obtención de datos de beneficiarios de subvenciones.

    Esta clase encapsula la lógica para interactuar con el servicio de
    InfoSubvenciones, procesar las respuestas y estructurar los datos para
    su uso posterior en el sistema.
    """

    def __init__(self):
        """Inicializa el agente y el servicio de subvenciones."""
        self.infosubvenciones_service = info_subvenciones_service
        self.node_name = "get_beneficiaries_node"

    def _parse_years(self, extracted_years_str: str) -> list[int]:
        """
        Parsea la cadena de años extraída y la convierte en una lista de enteros.
        """
        if not extracted_years_str:
            logger.warning("%s: No se proporcionaron años para la búsqueda.", self.node_name)
            return None

        try:
            target_years = [
                int(year.strip()) for year in extracted_years_str.split(',')
                if year.strip().isdigit()
            ]
            if not target_years:
                raise ValueError("La cadena procesada no contiene años válidos.")
            return target_years
        except ValueError:
            logger.warning(
                "%s: Formato de años inválido: '%s'.", self.node_name, extracted_years_str
            )
            return None

    def _initialize_api_data(self, years: list[int]) -> dict:
        """Inicializa el diccionario para almacenar los datos de la API."""
        return {year: [] for year in years}

    def _process_beneficiary_item(self, item: dict, api_data: dict):
        """

        Procesa un único ítem de beneficiario de la respuesta de la API y lo clasifica por año.
        """
        item_year_field = item.get('ejercicio')
        if item_year_field is None:
            logger.warning(
                "%s: El ítem de beneficiario no contiene el campo 'ejercicio': %s",
                self.node_name, str(item)[:100]
            )
            return

        try:
            item_year_int = int(item_year_field)
            if item_year_int in api_data:
                api_data[item_year_int].append(item)
            else:
                logger.warning(
                    "%s: La API devolvió datos para el año %d, que no fue solicitado. Datos: %s",
                    self.node_name, item_year_int, item
                )
        except ValueError:
            logger.warning(
                "%s: Valor de 'ejercicio' no entero ('%s') en el ítem: %s",
                self.node_name, item_year_field, item
            )

    def _process_api_response(self, response: Any, api_data: dict):
        """Procesa la respuesta completa de la API, ya sea una lista o un diccionario."""
        beneficiaries_list = []
        if isinstance(response, dict) and 'content' in response:
            beneficiaries_list = response['content']
            if not isinstance(beneficiaries_list, list):
                logger.warning(
                    "%s: La clave 'content' no es una lista. Tipo: %s",
                    self.node_name, type(beneficiaries_list)
                )
                return
        elif isinstance(response, list):
            beneficiaries_list = response
        else:
            logger.warning(
                "%s: Respuesta inesperada de la API. Tipo: %s", self.node_name, type(response)
            )
            return

        if not beneficiaries_list:
            logger.info("%s: La API no devolvió beneficiarios.", self.node_name)

        for item in beneficiaries_list:
            self._process_beneficiary_item(item, api_data)

    def _handle_api_error(self, years: list[int], error: Exception) -> dict:
        """Gestiona los errores ocurridos durante la llamada a la API."""
        error_msg = f"Error al obtener datos para los años {years}: {error}"
        logger.error(error_msg, exc_info=True)
        return {
            "api_response_data": {
                year: f"Error al obtener datos para el año {year}." for year in years
            },
            "error_message": error_msg
        }

    def get_beneficiaries_by_year(self, state: GraphState) -> dict:
        """
        Obtiene los beneficiarios por año a partir del estado proporcionado.

        Args:
            state: El objeto GraphState que contiene los años extraídos.

        Returns:
            Un diccionario con los datos de la API, un mensaje de error si lo hay,
            y el nombre del nodo actual.
        """
        extracted_years_str = state.get("extracted_years")
        logger.info(
            "%s: Años extraídos del estado: '%s'", self.node_name, extracted_years_str
        )

        target_years = self._parse_years(extracted_years_str)
        if not target_years:
            return {
                "api_response_data": {},
                "error_message": "No se proporcionaron años válidos.",
                "last_stream_event_node": self.node_name
            }

        api_data = self._initialize_api_data(target_years)
        error_to_propagate = None

        try:
            logger.info("%s: Consultando la API para los años: %s", self.node_name, target_years)
            api_response = self.infosubvenciones_service.obtener_beneficiarios_por_anno(
                target_years
            )
            self._process_api_response(api_response, api_data)

        except Exception as e:  # pylint: disable=broad-exception-caught
            error_result = self._handle_api_error(target_years, e)
            api_data = error_result["api_response_data"]
            error_to_propagate = error_result["error_message"]

        for year in target_years:
            if not api_data.get(year):
                api_data[year] = f"No se encontraron datos para el año {year}."

        log_data = json.dumps(api_data, ensure_ascii=False, indent=2)
        logger.info("%s: Datos estructurados para el generador: %s", self.node_name, log_data)

        return {
            "api_response_data": api_data,
            "error_message": state.get("error_message") or error_to_propagate,
            "last_stream_event_node": self.node_name
        }
