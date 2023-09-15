# Study of the potential use of the PoS algorithm in Internet of Things networks
*Proof of Trust simulation*

### Author:
- Paweł Podgórski

### Problems:
 - [ ] Save self_node to nodes in blockchain
 - [ ] Ustalenie jaka jest struktura transakcji i bloku
 - [ ] Czy self_node będzie trzymany jako global czy jako pierwszy obiekt z list nodes


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
python -m flask -app pos/start_node_flask run
```

Full simulation can be start using docker configuration file `docker-compose.yaml`:
```shell
docker compose up
```