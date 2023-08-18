class PublicKeyNotFoundException(Exception):
    pass


class PoSException(Exception):
    message: dict
    code: int

    def __init__(self, message: dict, code: int):
        self.message = message
        self.code = code
