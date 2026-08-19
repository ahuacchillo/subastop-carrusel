# Estudio VMC Subastas — la misma herramienta, dentro de un contenedor.
#
# NO ESTÁ EN USO. El estudio corre en local y así se queda; esto es la salida
# de emergencia para el día que se decida exponerlo. Construido y probado: el
# render completo sale en 13 s aquí dentro, con un pico de 704 MiB — que es
# justo el número que descarta los planes gratuitos de 512 MB. El porqué de
# todo esto está en el README.
#
# Nada del código cambia aquí: `estudio.py` toma host, puerto y clave del
# entorno y el resto corre igual que en el escritorio. Lo que resuelve esta
# imagen es que el render necesita un Chromium de verdad, y eso pide un
# contenedor y no una función serverless.
#
#   docker build -t estudio .
#   docker run -p 7860:7860 -e ESTUDIO_CLAVE=loquesea estudio
#
# Node de base y python encima: node trae la mitad pesada (Remotion), y python
# aquí es solo el intérprete de la stdlib, sin un paquete que instalar.
FROM node:20-bookworm-slim

# Las librerías de sistema que Chromium necesita para arrancar headless. Sin
# ellas el navegador falla al abrir y el render muere sin decir por qué.
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
      ca-certificates fonts-liberation \
      libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Sin privilegios: la imagen de node ya trae el usuario `node` con UID 1000, que
# es además el que esperan casi todos los alojamientos de contenedores. La app
# escribe (fotos, renders) dentro de su propio directorio, así que el dueño de
# los archivos tiene que ser ese mismo usuario.
#
# El mkdir explícito no sobra: WORKDIR crea la carpeta como root en el builder
# clásico de docker —el que usa Cloud Build— aunque USER ya esté puesto. Con
# BuildKit sale bien y el fallo no aparece hasta que se construye en la nube:
# `mkdir: cannot create directory 'Posts': Permission denied`.
RUN mkdir -p /home/node/app && chown node:node /home/node/app
USER node
WORKDIR /home/node/app

# Las dependencias antes que el código: mientras package-lock.json no cambie,
# reconstruir tras editar estudio.py no vuelve a bajar los 630 MB.
COPY --chown=node:node remotion/package.json remotion/package-lock.json ./remotion/
RUN cd remotion && npm ci

# Chromium horneado en la imagen. Si no, el primer render de cada arranque en
# frío se pone a descargar 150 MB y parece que la herramienta se colgó.
RUN cd remotion && npx remotion browser ensure

COPY --chown=node:node . .

# Los directorios de trabajo, creados de antemano: en el contenedor no existen
# porque están en .dockerignore, y son efímeros a propósito — el carrusel se
# baja en ZIP, así que no hace falta disco que sobreviva al reinicio.
RUN mkdir -p Posts Materiales remotion/public/autos

ENV ESTUDIO_HOST=0.0.0.0 \
    PORT=7860 \
    PYTHONUNBUFFERED=1

EXPOSE 7860
CMD ["python3", "estudio.py"]
