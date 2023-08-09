from random import randint


def get_random_from_list(object_list: list):
    return object_list[randint(0, len(object_list))]
