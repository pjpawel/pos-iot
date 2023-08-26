FROM python:3.11-alpine

WORKDIR /app

COPY . .
COPY .env.docker .env

RUN pip3 install -r requirements.txt

EXPOSE 5000
ENTRYPOINT [ "python3", "-m", "flask", "--app", "pos/start_node_flask", "run", "--host=0.0.0.0" ]