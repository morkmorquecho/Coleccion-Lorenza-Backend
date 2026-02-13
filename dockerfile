FROM python:3.11-slim

# Variables limpias
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app


# Dependencias del sistema + ODBC + build tools
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor \
        -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pipenv
RUN pip install --upgrade pip pipenv

# Copiamos Pipfiles primero (cache friendly)
COPY Pipfile Pipfile.lock ./

# Instala todas las dependencias de Python directamente en el sistema
RUN pipenv install --system --deploy

# Copiamos el proyecto
COPY . .

# Expone el puerto del server Django
EXPOSE 8000

# Comando para iniciar Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
