"""
Este módulo proporciona un servicio para interactuar con la API del
Sistema Nacional de Ayudas y Subvenciones de España.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


class ApiServiceError(Exception):
    """Excepción personalizada para errores ocurridos en el servicio de la API."""

class InfosubvencionesService:
    """
    Servicio para comunicarse con la API del Sistema Nacional de Ayudas y Subvenciones.
    """
    def __init__(self):
        """Inicializa el servicio con la URL base de la API."""
        self.base_url = "https://www.infosubvenciones.es/bdnstrans/api"
        self.logger = logging.getLogger(__name__)

    def buscar_convocatorias(self, params, max_workers=5):
        """
        Busca convocatorias en la API utilizando los parámetros proporcionados,
        y recupera los detalles en paralelo con threads.
        Args:
            params (dict): Diccionario con los parámetros de búsqueda.
            max_workers (int): Número máximo de hilos concurrentes.
        Returns:
            dict: Resultados de la búsqueda con detalle de cada convocatoria.
        """
        url = f"{self.base_url}/convocatorias/busqueda"
        self.logger.info("Buscando convocatorias con params: %s y URL: %s", params, url)

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            numeros = [
                item.get("numeroConvocatoria")
                for item in data.get("content", [])
                if item.get("numeroConvocatoria") is not None
            ]

            # Ahora es un dict en lugar de lista
            convocatorias_details = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_num = {
                    executor.submit(self.obtener_convocatoria, num): num
                    for num in numeros
                }
                for future in as_completed(future_to_num):
                    num = future_to_num[future]
                    try:
                        future_result = future.result()
                        convocatorias_details[str(future_result['id'])] = {
                            'presupuestoTotal': future_result['presupuestoTotal'],
                            'regiones': future_result['regiones'],
                            'tiposBeneficiarios': future_result['tiposBeneficiarios']
                        }
                    except ApiServiceError as e:
                        self.logger.error("Error al obtener convocatoria %s: %s", num, e)

            data["convocatoriasDetails"] = convocatorias_details
            return data
        except requests.RequestException as e:
            self.logger.error("Error en la petición de búsqueda: %s", e)
            raise ApiServiceError("No se pudo buscar convocatorias") from e


    def obtener_convocatoria(self, id_convocatoria):
        """
        Obtiene los detalles de una convocatoria específica.
        Args:
            id_convocatoria (str): ID de la convocatoria a consultar.
        Returns:
            dict: Detalles de la convocatoria.
        """
        try:
            url = f"{self.base_url}/convocatorias"
            params = {"numConv": id_convocatoria}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            msg = f"Error al obtener detalles de la convocatoria: {str(e)}"
            self.logger.error("Error al obtener convocatoria %s: %s",
                              id_convocatoria, str(e))
            raise ApiServiceError(msg) from e

    def obtener_beneficiarios_por_anno(self, lista_annos):
        """
        Obtiene los beneficiarios dada una lista de años.
        Args:
            lista_annos (list): Lista de años para consultar.
        Returns:
            dict: Beneficiarios por año.
        """
        try:
            url = f"{self.base_url}/grandesbeneficiarios/busqueda"
            params = {"anios": list(map(int, lista_annos))}
            self.logger.info("Obteniendo beneficiarios para años: %s con URL: %s",
                             lista_annos, url)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            msg = f"Error al comunicarse con la API de Infosubvenciones: {str(e)}"
            self.logger.error("Error al obtener beneficiarios por año: %s", str(e))
            raise ApiServiceError(msg) from e

    def buscar_partidos_politicos(self, params):
        """
        Busca partidos políticos en la API utilizando los parámetros proporcionados.
        Args:
            params (dict): Diccionario con los parámetros de búsqueda.
        Returns:
            dict: Resultados de la búsqueda de partidos políticos.
        """
        try:
            url = f"{self.base_url}/partidospoliticos/busqueda"
            self.logger.info(
                "Buscando partidos políticos con params: %s y URL: %s",
                params, url
            )
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Lanza excepción si hay error HTTP
            return response.json()
        except requests.exceptions.RequestException as e:
            msg = f"Error al comunicarse con la API de Infosubvenciones: {str(e)}"
            self.logger.error("Error al buscar partidos políticos: %s", str(e))
            raise ApiServiceError(msg) from e

info_subvenciones_service = InfosubvencionesService()
