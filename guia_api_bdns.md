# Documentación de la API de SNPSAP

Esta documentación describe cómo interactuar con la **API de SNPSAP (Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas)**. El objetivo de la API es proveer la información de carácter público que se encuentra registrada en la base de datos de subvenciones BDNS.

- **Versión de la API:** 1.1.0
- **Términos de Servicio:** [https://www.igae.pap.hacienda.gob.es/](https://www.igae.pap.hacienda.gob.es/)
- **Contacto de Soporte:** [soportetecnicobdns@igae.hacienda.gob.es](mailto:soportetecnicobdns@igae.hacienda.gob.es)

## Cómo Empezar

### URL Base de la API

La API está disponible en varios servidores. Puedes usar cualquiera de las siguientes URLs base para tus peticiones:

- `https://www.infosubvenciones.es/bdnstrans/api`
- `https://www.infosubvenciones.gob.es/bdnstrans/api`
- `https://www.pap.hacienda.gob.es/bdnstrans/api`
- `https://www.subvenciones.gob.es/bdnstrans/api`

En los ejemplos de Python, usaremos `https://www.infosubvenciones.es/bdnstrans/api`.

### Instalación (Python)

Para seguir los ejemplos, necesitas tener la librería `requests` instalada.

```bash
pip install requests
```

### Autenticación

Algunos endpoints, especialmente los relacionados con la gestión de suscripciones, requieren autenticación mediante un Token JWT. Este token debe ser incluido en la cabecera de la petición de la siguiente manera:

`Authorization: Bearer <TU_TOKEN_JWT>`

El token se obtiene a través de los endpoints de login o alta de suscripción.

---

## Convocatorias

Endpoints para consultar información sobre las convocatorias con publicidad registradas.

### `GET /convocatorias/busqueda`

Obtiene una lista paginada de convocatorias según los filtros especificados.

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `page` | Número de página. | integer | No | `0` |
| `pageSize` | Tamaño de página. | integer | No | `10` |
| `descripcion` | Cadena con el título o parte de él. | string | No | `"Resolución"` |
| `descripcionTipoBusqueda` | Tipo de búsqueda en el título (1: todas, 2: alguna, 0: frase exacta). | integer | No | `0` |
| `numeroConvocatoria` | Código BDNS a buscar. | string | No | `"376046"` |
| `mrr` | Filtrar por Mecanismo de Recuperación y Resiliencia. | boolean | No | `false` |
| `fechaDesde` | Fecha de inicio del periodo (formato `dd/mm/yyyy`). | string | No | `"01/01/2023"` |
| `fechaHasta` | Fecha de fin del periodo (formato `dd/mm/yyyy`). | string | No | `"31/01/2023"` |
| `tipoAdministracion` | Tipo de órgano (C: Estado, A: C. Autónoma, L: Local, O: Otros). | string | No | `"A"` |
| `organos` | Lista de identificadores de los órganos administrativos. | array[string] | No | `['713', '4730']` |
| `regiones` | Lista de identificadores de las regiones de impacto. | array[integer] | No | `[3, 50]` |
| `...` | (Y otros filtros disponibles en la especificación). | | | |

**Respuesta Exitosa (200 OK):**

Retorna un objeto JSON con una lista de convocatorias y metadatos de paginación.

```json
{
  "content": [
    {
      "id": 577594,
      "mrr": false,
      "numeroConvocatoria": "376046",
      "descripcion": "Resolución del 4 de diciembre de 2017...",
      "fechaRecepcion": "2017-12-18",
      "nivel1": "GALICIA",
      "nivel2": "AGENCIA GALLEGA DE LAS INDUSTRIAS CULTURALES (AGADIC)",
      "nivel3": null,
      "codigoINVENTE": "INV00000108"
    }
  ],
  "totalElements": 1,
  "totalPages": 1,
  "number": 0
}
```

**Ejemplo de Petición (Python):**

```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/convocatorias/busqueda"

# Parámetros para buscar convocatorias de la Comunidad Autónoma de Galicia (código de región 3)
# que contengan la palabra "audiovisuales"
params = {
    'descripcion': 'audiovisuales',
    'descripcionTipoBusqueda': 2, # alguna de las palabras
    'regiones': [3],
    'pageSize': 5
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()  # Lanza un error para códigos de estado 4xx/5xx

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"\nTotal de convocatorias encontradas: {data.get('totalElements')}")

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
except json.JSONDecodeError:
    print("Error: La respuesta no es un JSON válido.")

```

### `GET /convocatorias/{numConv}`

Obtiene el detalle completo de una convocatoria específica.
*(Nota: El endpoint en la especificación es `/convocatorias` con un parámetro `numConv`. Se representa aquí de forma más RESTful para claridad).*

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `numConv` | Número de la convocatoria (código BDNS). | string | Sí | `"406718"` |

**Ejemplo de Petición (Python):**

```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/convocatorias"

params = {
    'numConv': '406718'
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")

```

### `GET /convocatorias/exportar`

Exporta los resultados de una búsqueda de convocatorias a un archivo (PDF, XLSX o CSV).

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `tipoDoc` | Formato del documento de salida. | string | Sí | `"pdf"`, `"xlsx"`, `"csv"` |
| `vpd` | Identificador del portal. | string | Sí | `"GE"` |
| `...` | (Acepta los mismos filtros que `/convocatorias/busqueda`). | | | |

**Ejemplo de Petición (Python):**

```python
import requests

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/convocatorias/exportar"

params = {
    'tipoDoc': 'csv',
    'vpd': 'GE',
    'descripcion': 'ayudas cultura',
    'fechaDesde': '01/01/2023'
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()

    # Guardar el contenido en un archivo
    file_extension = params['tipoDoc']
    with open(f"exportacion_convocatorias.{file_extension}", "wb") as f:
        f.write(response.content)

    print(f"Archivo 'exportacion_convocatorias.{file_extension}' guardado correctamente.")

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```
---
## Concesiones

Endpoints para consultar información sobre las concesiones registradas.

### `GET /concesiones/busqueda`
Obtiene una lista paginada de concesiones según los filtros especificados.

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `page` | Número de página. | integer | No | `0` |
| `pageSize` | Tamaño de página. | integer | No | `10` |
| `numeroConvocatoria` | Código BDNS de la convocatoria asociada. | string | No | `"553219"` |
| `codConcesion` | Código de la concesión a buscar. | string | No | `"66715687"` |
| `nifCif` | NIF/CIF del beneficiario. | string | No | `"A12345678"` |
| `fechaDesde` | Fecha de inicio del periodo (formato `dd/mm/yyyy`). | string | No | `"01/01/2022"` |
| `fechaHasta` | Fecha de fin del periodo (formato `dd/mm/yyyy`). | string | No | `"31/12/2022"` |
| `...` | (Y otros filtros disponibles en la especificación). | | | |

**Respuesta Exitosa (200 OK):**

Retorna un objeto JSON con una lista de concesiones y metadatos de paginación.

```json
{
  "content": [
    {
      "id": 66715687,
      "idConvocatoria": 754779,
      "numeroConvocatoria": "553219",
      "convocatoria": "Avales a financiación a empresas y autónomos...",
      "fechaConcesion": "2022-05-20",
      "idPersona": 11962600,
      "beneficiario": "***3410** JUAN RAUL LOPEZ -",
      "instrumento": "GARANTÍA",
      "importe": 64000,
      "ayudaEquivalente": 8538.32,
      "tieneProyecto": false
    }
  ],
  "totalElements": 1
}
```

**Ejemplo de Petición (Python):**

```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/concesiones/busqueda"

# Buscar concesiones para un NIF/CIF específico
params = {
    'nifCif': 'B35236355', # Ejemplo de la documentación
    'pageSize': 5
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```
---

## Ayudas de Estado

Endpoints para consultar concesiones clasificadas como Ayudas de Estado.

### `GET /ayudasestado/busqueda`

Obtiene una lista paginada de concesiones de Ayuda de Estado según filtros.

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `ayudaEstado`| SA Number - Referencia de ayuda de estado (sólo cifras). | string | No | `"48422"` |
| `objetivos` | Lista de identificadores de los objetivos de la concesión. | array[integer] | No | `[167]` |
| `reglamento`| Identificador del reglamento. | integer | No | `6` |
| `...` | (Acepta filtros comunes como `nifCif`, `fechaDesde`, etc.). | | | |

**Respuesta Exitosa (200 OK):**

Retorna un objeto JSON con la lista de ayudas.

```json
{
  "content": [
    {
      "idConcesion": 24666326,
      "numeroConvocatoria": "307701",
      "convocatoria": "Subvenciones a los seguros de acuicultura marina 2017",
      "convocante": "ESTADO MINISTERIO DE AGRICULTURA...",
      "reglamento": "REG (UE) 1388/2014, DE 16 DE DICIEMBRE...",
      "objetivo": "ART. 40 AYUDAS PARA SEGUROS DE LAS POBLACIONES ACUÍCOLAS",
      "beneficiario": "B35236355 AQUANARIA S.L.",
      "importe": 235704.95,
      "ayudaEstado": "SA.48422",
      "urlAyudaEstado": "http://ec.europa.eu/competition/elojade/isef/case_details.cfm?proc_code=3_SA_48422"
    }
  ]
}
```

**Ejemplo de Petición (Python):**

```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/ayudasestado/busqueda"

# Buscar ayudas de estado por su SA Number
params = {
    'ayudaEstado': '48422',
    'pageSize': 2
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```

---

## Catálogos

Endpoints para obtener listas de valores utilizados en los filtros de búsqueda (catálogos).

### `GET /regiones`

Obtiene todas las regiones disponibles en una estructura de árbol.

**Ejemplo de Petición (Python):**
```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/regiones"

try:
    response = requests.get(f"{BASE_URL}{endpoint}")
    response.raise_for_status()

    data = response.json()
    print("Regiones disponibles (primer nivel):")
    for region in data:
        print(f"- ID: {region.get('id')}, Descripción: {region.get('descripcion')}")

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```

### `GET /finalidades`

Obtiene todas las finalidades (políticas de gasto) disponibles.

**Ejemplo de Petición (Python):**
```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/finalidades"

try:
    response = requests.get(f"{BASE_URL}{endpoint}")
    response.raise_for_status()

    data = response.json()
    print("Finalidades disponibles:")
    for finalidad in data:
        print(f"- ID: {finalidad.get('id')}, Descripción: {finalidad.get('descripcion')}")

except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```
### `GET /organos`
Obtiene los órganos administrativos para un tipo de administración específico.

**Parámetros de consulta:**

| Parámetro | Descripción | Tipo | Requerido | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `idAdmon` | Tipo de órgano (C: Estado, A: C. Autónoma, L: Local, O: Otros).| string | Sí | `"A"` |
| `vpd` | Identificador del portal. | string | No | `"GE"` |

**Ejemplo de Petición (Python):**

```python
import requests
import json

BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
endpoint = "/organos"

# Obtener órganos para las Comunidades Autónomas
params = {
    'idAdmon': 'A'
}

try:
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    response.raise_for_status()

    data = response.json()
    print("Órganos de Comunidades Autónomas (primer nivel):")
    for organo in data:
        print(f"- ID: {organo.get('id')}, Descripción: {organo.get('descripcion')}")


except requests.exceptions.RequestException as e:
    print(f"Error en la petición: {e}")
```