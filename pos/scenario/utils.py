import logging
from random import randint


def get_random_from_list(object_list: list):
    return object_list[randint(0, len(object_list) - 1)]


def print_runtime_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(e)
            print(e)
            raise e
    return inner
