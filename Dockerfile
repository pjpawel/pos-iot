FROM python:3.11-alpine

WORKDIR /app

COPY . .
COPY .env.docker .env
COPY docker/docker-entrypoint.sh docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh

RUN pip3 install -r requirements_docker.txt

EXPOSE 5000
ENTRYPOINT [ "./docker-entrypoint.sh" ]