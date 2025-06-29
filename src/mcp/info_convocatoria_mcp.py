"""
# info_convocatoria_mcp.py
"""
import io
import logging
from urllib.parse import urljoin
import os
import PyPDF2
from fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

server = FastMCP("MyAssistantServer")

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def get_pdf_content(url: str) -> str:
    """
    Función para obtener el contenido de un PDF desde una URL.
    
    :param url: URL del PDF a descargar.
    :return: Contenido del PDF como string.
    """
    logger.info("Iniciando extracción de PDF desde:  %s", url)
    response = requests.get(url, timeout=15)
    pdf_io_bytes = io.BytesIO(response.content)
    text_list = []
    pdf = PyPDF2.PdfReader(pdf_io_bytes)

    num_pages = len(pdf.pages)
    logger.info("PDF obtenido con %s páginas.", num_pages)

    for page in range(num_pages):
        page_text = pdf.pages[page].extract_text()
        text_list.append(page_text)
    text = "\n".join(text_list)
    return text


# 3. Usar la instancia 'server' para los decoradores
@server.tool
def get_info_convo(url: str) -> str:
    """
    Herramienta para obtener el contenido de texto y todos los enlaces de una URL
    en un único string.
    
    :param url: URL de la página a scrapear.
    :return: Un solo string con el texto de la página seguido de todos los 
             enlaces únicos encontrados.
    """
    try:
        logger.info("Obteniendo información de la URL: %s", url)
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Lanza un error si la solicitud HTTP falla

        soup = BeautifulSoup(response.content, 'html.parser')
        # 1. Extraer todo el texto de la página de forma limpia
        page_text = soup.get_text(separator=' ', strip=True)

        # 2. Encontrar todos los enlaces únicos
        unique_links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            # Ignorar enlaces vacíos o que solo son anclas en la misma página
            if href and not href.startswith('#'):
                # Convertir enlaces relativos (ej: /contacto) a absolutos
                full_url = urljoin(url, href)
                unique_links.add(full_url)
        # 3. Formatear la lista de enlaces como un string
        # Usamos '\n' para que cada enlace aparezca en una nueva línea
        filtered_links = {link for link in unique_links if "pdf" in link.lower()}

        # 4. Si hay enlaces a PDFs, extraer su contenido
        pdf_content = '\n'.join([get_pdf_content(link) for link in filtered_links])

        # 5. Combinar el texto y los enlaces en un solo string de salida
        final_output = (
            f"{page_text}\n\n"
            f"\n\n--- CONTENIDO DE LOS PDFS ---\n"
            f"{pdf_content}"
        )
        logger.info("Contenido obtenido y combinado correctamente, procediendo al resumen.")
        return summarise_via_llm(final_output)

    except requests.exceptions.RequestException as e:
        error_message = f"Error al procesar la URL {url}: {e}"
        logger.error(error_message)
        return error_message

def summarise_via_llm(text: str) -> str:
    """
    Función para resumir un texto usando el modelo LLM de Mistral.
    
    :param text: Texto a resumir.
    :return: Resumen del texto.
    """
    logger.info("Enviando texto al LLM para resumen.")
    response = gemini_client.models.generate_content(
        model=os.environ["GEMINI_MODEL"],
        contents="Dado el siguiente texto, por favor, proporciona un resumen, tanto de la página web como de los PDFs incluidos:\n\n" + text
    )
    logger.info("Resumen obtenido correctamente.")
    return response.text

# 4. Ejecutar la instancia del servidor que ya tiene las herramientas registradas
if __name__ == "__main__":
    logger.info("Servidor MCP (info_convocatoria_mcp.py) iniciando...")
    # El método run() inicia el servidor y lo mantiene a la escucha.
    server.run(transport="streamable-http", host="127.0.0.1", port=8000)