"""
Pruebas unitarias para las funciones de enrutamiento de GraphState.
"""
import pytest
from src.graph.graph import should_extract, should_call_api


# Para estas pruebas, no necesitamos un objeto GraphState completo,
# solo un diccionario que simule el estado que las funciones necesitan.

# -- Pruebas para la función should_extract --

# @pytest.mark.parametrize nos permite ejecutar la misma prueba con diferentes datos.
# Es una forma muy eficiente de probar todas las ramas de una función.
@pytest.mark.parametrize("intent, expected_node", [
    ("OBTENER_CONVOCATORIA_DETALLES", "extract_convocatoria_id_node"),
    ("BUSCAR_CONVOCATORIAS_GENERAL", "extract_search_params_node"),
    ("BUSCAR_BENEFICIARIOS_POR_ANNO", "extract_years_node"),
    ("BUSCAR_PARTIDOS_POLITICOS", "extract_party_params_node"),
    ("GENERAL_CONVERSATION", "generate_general_response_node"),
    ("INTENCION_DESCONOCIDA", "error_handler"), # Probar el caso por defecto
    (None, "error_handler"), # Probar qué pasa si la intención es None
])
def test_should_extract_routes_by_intent(intent, expected_node):
    """
    Verifica que should_extract direcciona correctamente según la intención.
    """
    # 1. Preparar el estado de prueba
    mock_state = {"intent": intent}

    # 2. Ejecutar la función que estamos probando
    result = should_extract(mock_state)

    # 3. Comprobar que el resultado es el esperado (esto es una aserción)
    assert result == expected_node

def test_should_extract_goes_to_error_handler_if_error_message_exists():
    """
    Verifica que, sin importar la intención, se direccione al manejador de errores
    si ya existe un error en el estado.
    """
    mock_state = {
        "intent": "OBTENER_CONVOCATORIA_DETALLES",
        "error_message": "Un error previo ocurrió"
    }
    result = should_extract(mock_state)
    assert result == "error_handler"


# -- Pruebas para la función should_call_api --

@pytest.mark.parametrize("intent, expected_node", [
    ("OBTENER_CONVOCATORIA_DETALLES", "call_infosubvenciones_get_details_node"),
    ("BUSCAR_CONVOCATORIAS_GENERAL", "call_infosubvenciones_search_node"),
    ("BUSCAR_BENEFICIARIOS_POR_ANNO", "get_beneficiaries_node"),
    ("BUSCAR_PARTIDOS_POLITICOS", "search_political_parties_node"),
])
def test_should_call_api_routes_correctly(intent, expected_node):
    """
    Verifica que should_call_api direcciona a la API correcta.
    """
    mock_state = {"intent": intent, "error_message": None}
    result = should_call_api(mock_state)
    assert result == expected_node

def test_should_call_api_goes_to_error_handler_for_unhandled_intent():
    """
    Verifica que una intención sin una API asociada vaya al manejador de errores.
    """
    mock_state = {"intent": "GENERAL_CONVERSATION"} # Esta intención no llama a una API
    result = should_call_api(mock_state)
    assert result == "error_handler"
