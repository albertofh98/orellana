# Archivo: cliente.py (o como lo llames)

from fastmcp import Client
import asyncio

config = {
    "mcpServers": {
        "MyAssistantServer": {"command": "python3", "args": ["info_convocatoria_mcp.py"]}
    }
}

client = Client(config)

async def main():
    async with client:        
        # --- ESTE ES EL CAMBIO CLAVE ---
        # En lugar de: await client.MyAssistantServer.multiply(a=3, b=4)
        # Usamos el método call_tool con el nombre completo como string.
        # El formato es "NombreDelServidor.nombre_herramienta"
        answer = await client.call_tool("get_info_convo", 
                                        {"url": "https://sede.vigo.org/expedientes/avisos/aviso.jsp?id=4866&lang=ga"
                                         }
                                         )
        print(f"Cliente: El servidor devolvió el resultado: {answer}")

if __name__ == "__main__":
    asyncio.run(main())
