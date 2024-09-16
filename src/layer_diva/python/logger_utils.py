from typing import Callable
from aws_lambda_powertools import Logger


log = Logger()


def log_io(func: Callable):
    def wrapper(*args, **kwargs):
        log.info(f"Calling function {func.__name__} with: {args} {kwargs}")
        try: 
            res = func(*args,**kwargs)
            log.info(f"Function {func.__name__} responded with: {res}")
            return res
        except Exception as e:
            log.error(f"Function {func.__name__} failed with error: {e}")
            raise e

    return wrapper

def log_error(func: Callable):
    def wrapper(*args, **kwargs):
        try: 
            res = func(*args,**kwargs)
            return res
        except Exception as e:
            log.error(f"Function {func.__name__} failed with error: {e}")
            raise e

    return wrapper