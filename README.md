# Study of the potential use of the PoS algorithm in Internet of Things networks
*Proof of Staked Trust blockchain simulation*

### Author:
- Paweł Podgórski

### Environment setup

1. Clone repository
    ```shell
    git clone git@github.com:pjpawel/pos-iot.git
    ```
2. Create python virtual environment
    ```shell
    python -m venv env
    ```
3. Install all dependencies
    ```shell
   pip install -r requirements.txt 
   ```

### How to run

There is 2 ways to start simulation. In simplest way is by calling flask:
```shell
python -m flask -app post/start_node_flask run
```

Full simulation can be start using docker configuration file `docker-compose.yaml`:
```shell
docker compose up
```

Zatwierdzanie walidatorów:
- 50% walidatorów nie może być taka sama.
- urządzenie może się nie zgodzić na bycie walidatorem

