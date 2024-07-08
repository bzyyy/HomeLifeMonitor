# Usa una imagen base oficial de Python
FROM python:3.11

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo de dependencias al contenedor
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el contenido de tu aplicación al contenedor
COPY . .

# Copia el archivo de credenciales al contenedor
COPY ancient-house-323902-8950ded2a98e.json /app/service-account-file.json

# Establece la variable de entorno en el contenedor
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service-account-file.json"

# Expone el puerto en el que la aplicación está corriendo
EXPOSE 8000

# Define el comando por defecto para ejecutar la aplicación
CMD ["python", "main.py"]
