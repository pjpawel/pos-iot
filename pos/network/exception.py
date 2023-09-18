class PublicKeyNotFoundException(Exception):
    pass


class PoSException(Exception):
    message: str
    code: int

    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code
