# Makefile para el proyecto Buscador de Subvenciones

# --- Variables ---
PYTHON = python3

# --- Reglas Phony ---
# Declara los objetivos que no son nombres de archivos.
.PHONY: all lint clean start

all: start

# --- Objetivos ---

# Ejecuta el linter (flake8) en el directorio de código fuente.
# Necesitarás instalar flake8: pip install flake8
lint:
	@echo "🔎  Ejecutando linter (flake8) en el código fuente..."
	$(PYTHON) -m flake8

# Limpia los archivos de caché de Python.
clean:
	@echo "🧹  Limpiando archivos de caché (.pyc) y directorios (__pycache__)..."
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "✨  Limpieza completada."

# Inicia la aplicación Flask.
start:
	@echo "🚀  Iniciando la aplicación Flask..."
	@echo "Puedes acceder a la aplicación en http://127.0.0.1:5000"
	$(PYTHON) main.py