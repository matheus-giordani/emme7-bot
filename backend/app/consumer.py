"""Consumer app - reading and processing Redis messages."""

import os
import time
import logging
import requests

from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future
from src.repositories.redis.redis_crud import RedisDatabase
from src.services.redis.redis_services import RedisService

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_SSL = os.getenv("REDIS_SSL")
CONSUMER_REDIS_TIME = os.getenv("CONSUMER_REDIS_TIME")
BACKEND_HOST = os.getenv("BACKEND_HOST")

assert (
    REDIS_HOST is not None
), "Variable REDIS_HOST from env file shouldn't be None, fill in the credential."
assert (
    CONSUMER_REDIS_TIME is not None
), "Variable CONSUMER_REDIS_TIME from env file shouldn't be None, fill in the credential."


CONSUMER_REDIS_TIME_INT = (
    int(CONSUMER_REDIS_TIME)
    if CONSUMER_REDIS_TIME and CONSUMER_REDIS_TIME.isdigit()
    else 60
)


# Configuração do logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_message(messages: List[Dict[str, Any]]) -> requests.models.Response:
    """
    Send a list of messages to a specified URL for processing and returns the response.

    Args:
        messages (List): A list of messages to be processed.

    Returns:
        str: The response from the server after processing the messages.
    """
    url = f"http://{BACKEND_HOST}/api/user/process_message"
    response = requests.post(url, json=messages)

    return response


def process_message_and_send_to_client(messages: List[Dict[str, Any]]) -> bool:
    """
    Process a list of messages and sends the processed message to a client.

    Args:
        messages (List): A list of messages to be processed.
        phone (str): The phone number of the client to send the processed message to.

    Returns:
        bool: True if the message was successfully sent to the client, False otherwise.
    """
    print("THESE ARE THE MESSAGES TO SEND")
    print(50 * "!")
    llm_message = process_message(messages=messages)
    print(50 * "))")
    # response_sent_to_client = send_to_client(llm_message=llm_message, phone=phone)
    if llm_message.status_code == 200:
        return True
    else:
        return False


def processer(workers: int = 10) -> None:
    """
    Continuously processes messages from a Redis queue using a thread pool.

    This function retrieves messages, organizes them by phone number and store_phone, and processes
    them concurrently while enforcing a worker limit. It also tracks failed attempts
    and removes messages that fail multiple times.

    Args:
        workers (int): The maximum number of concurrent worker threads. Defaults to 10.

    Behavior:
        - Fetches messages older than a threshold from the Redis database.
        - Groups messages by phone number + store_phone and queues them for processing.
        - Manages a thread pool to ensure concurrent processing.
        - Tracks processing attempts and retries failed messages.
        - Cleans up successfully processed messages.
        - Removes messages that fail more than three times.
    """
    logging.info("Iniciando o processador com %d workers.", workers)
    database = RedisService(
        RedisDatabase(
            host=REDIS_HOST, password=REDIS_PASSWORD, port=6379, ssl=REDIS_SSL
        )
    )
    pool = ThreadPoolExecutor(max_workers=workers)

    tasks: Dict[str, Future[bool]] = {}
    tries: Dict[str, int] = {}
    messages_dict: Dict[str, List[Dict[str, Any]]] = {}

    while True:
        # Verifica se existe mensagens mais antigas que X segundos e pega o número do telefone.
        key_list = []
        key_filter = {}
        messages = database.time_search(time_threshold_seconds=CONSUMER_REDIS_TIME_INT)
        logging.info("Mensagens encontradas na fila: %d", len(messages))
        # Para cada mensagem.
        for message in messages:
            print(message)
            phone = message.phone
            store_phone = str(message.store_phone)
            # Create composite key: phone + store_phone
            composite_key = f"{phone}_{store_phone}"
            print(composite_key)
            logging.debug("Processando mensagem para a chave: %s", composite_key)

            # Verifique se esta chave já está sendo processada.
            if composite_key not in tasks:

                # Salvando em key_list somente as chaves únicas em ordem de chegada.
                if composite_key not in key_filter:
                    key_list.append(composite_key)
                    key_filter[composite_key] = True

                # Salvando as mensagens associadas à chave para processamento.
                if composite_key not in messages_dict:
                    messages_dict[composite_key] = []
                messages_dict[composite_key].append(message.model_dump())

        # Enquanto houver chaves na lista e o máximo de tarefas/thread não ter sido atingido.
        while key_list and len(tasks) < workers:

            composite_key = key_list.pop(0)
            logging.info(
                "Adicionando chave %s na fila de processamento.", composite_key
            )
            tasks[composite_key] = pool.submit(
                process_message_and_send_to_client, messages_dict[composite_key]
            )

        # Verificando quais tarefas foram concluídas.
        done_tasks = []
        for composite_key in list(tasks.keys()):

            # Se a tarefa foi concluída.
            if tasks[composite_key].done():

                # Extraindo o resultado da tarefa.
                result = tasks[composite_key].result()
                logging.info(
                    "Processamento concluído para a chave %s com sucesso: %s",
                    composite_key,
                    result,
                )

                # Se a mensagem foi processada com sucesso.
                if result:
                    done_tasks.append(composite_key)

                    # Se a mensagem foi processada com insucesso anteriormente.
                    if composite_key in tries:
                        logging.debug(
                            "Resetando contagem de tentativas para a chave %s.",
                            composite_key,
                        )
                        tries[composite_key] = 4
                else:
                    # Adicione na lista as chaves que falharam.
                    if composite_key not in tries:
                        tries[composite_key] = 0
                    tries[composite_key] += 1
                    logging.warning(
                        "Falha ao processar chave %s. Tentativa %d.",
                        composite_key,
                        tries[composite_key],
                    )

        # Removendo as tarefas completas da lista de tarefas em execução.
        for composite_key in done_tasks:
            logging.info("Removendo chave %s das tarefas em execução.", composite_key)
            _ = tasks.pop(composite_key)
            database.delete_messages(messages_dict[composite_key])
            messages_dict.pop(composite_key)

        # Removendo as tarefas que falharam mais de 3 vezes.
        for composite_key in list(tries.keys()):
            if tries[composite_key] > 3:
                logging.error(
                    "Chave %s falhou mais de 3 vezes. Removendo mensagens associadas.",
                    composite_key,
                )
                database.delete_messages(messages_dict[composite_key])
                tries.pop(composite_key)
                messages_dict.pop(composite_key)
                tasks.pop(composite_key)

        logging.debug("Aguardando 2 segundos antes do próximo ciclo.")
        time.sleep(2)


if __name__ == "__main__":
    processer()
