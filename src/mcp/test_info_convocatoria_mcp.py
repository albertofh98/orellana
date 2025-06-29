"""
# test_info_convocatoria_mcp.py
"""
import asyncio
from fastmcp import Client

# URL de ejemplo para probar la herramienta del servidor.
# Puedes cambiarla por cualquier otra URL que quieras analizar.
# TEST_URL = "https://sede.vigo.org/expedientes/avisos/aviso.jsp?id=4866&lang=ga"
TEST_URL = "https://juntadeandalucia.es/boja/2024/251/2"

async def main():
    """
    Función principal para conectarse al servidor MCP y probar la herramienta.
    """
    print("Iniciando cliente MCP para probar el servidor...")

    # 1. Crear una instancia del cliente FastMCP.
    #    El nombre 'MyAssistantClient' es para identificar a este cliente.
    config = {
    "mcpServers": {
        "MyAssistantServer": {"url": "http://127.0.0.1:8000/mcp"},
        }
    }

    # Create a client that connects to all servers
    client = Client(config)

    async with client:
        # Access tools and resources with server prefixes
        response = await client.call_tool("get_info_convo", {"url": TEST_URL})
        print(f"Respuesta del servidor: {response}")

# Ejecutar la función principal asíncrona.
if __name__ == "__main__":
    asyncio.run(main())
