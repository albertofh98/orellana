A continuación se presenta un manual detallado en formato README.md sobre cómo realizar peticiones a los servicios GET de la API REST de la Base de Datos Nacional de Subvenciones de España, utilizando la librería `requests` de Python.

---

# Manual de Uso de la API REST de la Base de Datos Nacional de Subvenciones con Python

Este documento proporciona una guía detallada sobre cómo interactuar con los servicios GET de la API REST de la Base de Datos Nacional de Subvenciones (BDNS) de España. Se utilizará la librería `requests` de Python para realizar las peticiones.

## Instalación de la librería `requests`

Antes de comenzar, asegúrate de tener instalada la librería `requests`. Si no la tienes, puedes instalarla usando pip:

```bash
pip install requests
```

## Endpoints de la API

La URL base para todos los endpoints de la API es: `https://www.infosubvenciones.es/bdnstrans/v2/`

A continuación, se detallan todos los servicios GET disponibles, sus parámetros de entrada, los datos de salida y un ejemplo de cómo realizar la petición en Python.

---

### 1. Búsqueda de Convocatorias

Este servicio permite buscar convocatorias de subvenciones.

**Endpoint:** `/convocatorias/search`

#### Parámetros de Entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `q` | string | No | Texto libre para buscar en los campos de la convocatoria. |
| `titulo` | string | No | Búsqueda por el título de la convocatoria. |
| `finalidad` | string | No | Búsqueda por la finalidad de la convocatoria. |
| `idRegion` | string | No | Filtrar por el ID de la región. |
| `idCCAA` | string | No | Filtrar por el ID de la Comunidad Autónoma. |
| `idProvincia` | string | No | Filtrar por el ID de la provincia. |
| `idEntidadLocal` | string | No | Filtrar por el ID de la entidad local. |
| `idOrgano` | string | No | Filtrar por el ID del órgano convocante. |
| `codigoOrgano` | string | No | Filtrar por el código DIR3 del órgano convocante. |
| `fechaMin` | date | No | Fecha mínima de la convocatoria (formato `dd/MM/yyyy`). |
| `fechaMax` | date | No | Fecha máxima de la convocatoria (formato `dd/MM/yyyy`). |
| `page` | integer | No | Número de la página de resultados (por defecto 1). |
| `rows` | integer | No | Número de resultados por página (por defecto 10). |

#### Datos de Salida

| Campo | Tipo | Descripción |
|---|---|---|
| `numResultados` | integer | Número total de resultados encontrados. |
| `pagina` | integer | Número de la página actual. |
| `datos` | array | Lista de convocatorias. |
| `id` | integer | Identificador único de la convocatoria. |
| `titulo` | string | Título de la convocatoria. |
| `finalidad` | string | Descripción de la finalidad. |
| `organo` | string | Órgano convocante. |
| `codigoOrgano` | string | Código DIR3 del órgano. |
| `fechaRegistro` | string | Fecha de registro de la convocatoria. |
| `region` | string | Región. |
| `CCAA` | string | Comunidad Autónoma. |
| `provincia` | string | Provincia. |
| `entidadLocal` | string | Entidad Local. |
| `url` | string | URL a la convocatoria en el portal. |

#### Ejemplo en Python

```python
import requests

url = "https://www.infosubvenciones.es/bdnstrans/v2/convocatorias/search"
params = {
    "titulo": "ayudas a la investigación",
    "rows": 5
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    print("Número de resultados:", data.get("numResultados"))
    for convocatoria in data.get("datos", []):
        print("- Título:", convocatoria.get("titulo"))
        print("  Órgano:", convocatoria.get("organo"))
        print("  Fecha de Registro:", convocatoria.get("fechaRegistro"))
        print("-" * 20)
else:
    print("Error en la petición:", response.status_code)

```

---

### 2. Obtener Detalles de una Convocatoria

Este servicio permite obtener los detalles completos de una convocatoria específica a partir de su identificador.

**Endpoint:** `/convocatorias/{id}`

#### Parámetros de Entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | integer | Sí | Identificador único de la convocatoria. |

#### Datos de Salida

El objeto JSON devuelto contiene información detallada sobre la convocatoria, incluyendo título, finalidad, órgano convocante, fechas, e información presupuestaria.

#### Ejemplo en Python

```python
import requests

# Reemplazar con un ID de convocatoria válido
id_convocatoria = 12345 
url = f"https://www.infosubvenciones.es/bdnstrans/v2/convocatorias/{id_convocatoria}"

response = requests.get(url)

if response.status_code == 200:
    convocatoria = response.json()
    print("Título:", convocatoria.get("titulo"))
    print("Finalidad:", convocatoria.get("finalidad"))
    print("Órgano:", convocatoria.get("organoConvocante", {}).get("nombre"))
else:
    print("Error en la petición:", response.status_code)

```

---

### 3. Búsqueda de Concesiones

Este servicio permite buscar concesiones de subvenciones.

**Endpoint:** `/concesiones/search`

#### Parámetros de Entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `q` | string | No | Texto libre para buscar en los campos de la concesión. |
| `idConvocatoria` | integer | No | Filtrar por el ID de la convocatoria asociada. |
| `nifBeneficiario` | string | No | Filtrar por el NIF del beneficiario. |
| `nombreBeneficiario` | string | No | Búsqueda por el nombre del beneficiario. |
| `idRegion` | string | No | Filtrar por el ID de la región. |
| `idCCAA` | string | No | Filtrar por el ID de la Comunidad Autónoma. |
| `idProvincia` | string | No | Filtrar por el ID de la provincia. |
| `idEntidadLocal` | string | No | Filtrar por el ID de la entidad local. |
| `idOrgano` | string | No | Filtrar por el ID del órgano concedente. |
| `codigoOrgano` | string | No | Filtrar por el código DIR3 del órgano concedente. |
| `fechaMin` | date | No | Fecha mínima de la concesión (formato `dd/MM/yyyy`). |
| `fechaMax` | date | No | Fecha máxima de la concesión (formato `dd/MM/yyyy`). |
| `page` | integer | No | Número de la página de resultados (por defecto 1). |
| `rows` | integer | No | Número de resultados por página (por defecto 10). |

#### Datos de Salida

| Campo | Tipo | Descripción |
|---|---|---|
| `numResultados` | integer | Número total de resultados encontrados. |
| `pagina` | integer | Número de la página actual. |
| `datos` | array | Lista de concesiones. |
| `id` | integer | Identificador único de la concesión. |
| `convocatoriaBDNS`| integer | ID de la convocatoria en la BDNS. |
| `tituloConvocatoria`| string | Título de la convocatoria asociada. |
| `nombreBeneficiario`| string | Nombre del beneficiario. |
| `nifBeneficiario` | string | NIF del beneficiario. |
| `importe` | number | Importe de la concesión. |
| `fechaConcesion` | string | Fecha de la concesión. |
| `organoConcedente` | string | Órgano que realiza la concesión. |

#### Ejemplo en Python

```python
import requests

url = "https://www.infosubvenciones.es/bdnstrans/v2/concesiones/search"
params = {
    "nombreBeneficiario": "nombre de un beneficiario",
    "rows": 5
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    print("Número de resultados:", data.get("numResultados"))
    for concesion in data.get("datos", []):
        print("- Beneficiario:", concesion.get("nombreBeneficiario"))
        print("  Importe:", concesion.get("importe"), "EUR")
        print("  Fecha:", concesion.get("fechaConcesion"))
        print("-" * 20)
else:
    print("Error en la petición:", response.status_code)
```

---

### 4. Obtener Detalles de una Concesión

Este servicio permite obtener los detalles completos de una concesión específica a partir de su identificador.

**Endpoint:** `/concesiones/{id}`

#### Parámetros de Entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | integer | Sí | Identificador único de la concesión. |

#### Datos de Salida

El objeto JSON devuelto contiene información detallada sobre la concesión, incluyendo beneficiario, importe, fechas, y la convocatoria asociada.

#### Ejemplo en Python

```python
import requests

# Reemplazar con un ID de concesión válido
id_concesion = 12345 
url = f"https://www.infosubvenciones.es/bdnstrans/v2/concesiones/{id_concesion}"

response = requests.get(url)

if response.status_code == 200:
    concesion = response.json()
    print("Beneficiario:", concesion.get("beneficiario", {}).get("nombre"))
    print("Importe:", concesion.get("importe"))
    print("Instrumento de ayuda:", concesion.get("instrumentoAyuda"))
else:
    print("Error en la petición:", response.status_code)
```

---

### 5. Obtener Órganos

Este servicio devuelve una lista de los órganos que pueden aparecer como convocantes o concedentes.

**Endpoint:** `/organos`

#### Parámetros de Entrada

Ninguno.

#### Datos de Salida

Una lista de objetos, donde cada objeto representa un órgano con su `id` y `nombre`.

#### Ejemplo en Python

```python
import requests

url = "https://www.infosubvenciones.es/bdnstrans/v2/organos"

response = requests.get(url)

if response.status_code == 200:
    organos = response.json()
    print(f"Se encontraron {len(organos)} órganos.")
    # Imprimir los primeros 5 órganos
    for organo in organos[:5]:
        print(f"- ID: {organo.get('id')}, Nombre: {organo.get('nombre')}")
else:
    print("Error en la petición:", response.status_code)
```

---

### 6. Obtener Tipos de Beneficiario

Este servicio devuelve una lista de los tipos de beneficiarios.

**Endpoint:** `/tiposBeneficiario`

#### Parámetros de Entrada

Ninguno.

#### Datos de Salida

Una lista de objetos, donde cada objeto representa un tipo de beneficiario con su `id` y `nombre`.

#### Ejemplo en Python

```python
import requests

url = "https://www.infosubvenciones.es/bdnstrans/v2/tiposBeneficiario"

response = requests.get(url)

if response.status_code == 200:
    tipos_beneficiario = response.json()
    print("Tipos de beneficiario encontrados:")
    for tipo in tipos_beneficiario:
        print(f"- ID: {tipo.get('id')}, Nombre: {tipo.get('nombre')}")
else:
    print("Error en la petición:", response.status_code)
```