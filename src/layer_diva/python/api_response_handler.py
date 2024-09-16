import os
from aws_lambda_powertools import Logger
from src.layer_diva.python.api_gw_response import ApiGwResponse
class NotFoundError(Exception):
    pass

class BadRequest(Exception):
    pass

class Unauthorized(Exception):
    pass

class Forbidden(Exception):
    pass

log = Logger()

cors = os.environ.get("CORS", None)


def api_response_handler(func):
    def wrapper(event, context, **kwargs):

        try:
            return ApiGwResponse(200, func(event, context, **kwargs), cors=cors).to_json()
        except BadRequest as e:
            log.warning(e)
            return ApiGwResponse(400, cors=cors).to_json()
        except Unauthorized as e:
            log.warning(e)
            return ApiGwResponse(401, cors=cors).to_json()
        except Forbidden as e:
            log.warning(e)
            return ApiGwResponse(403, cors=cors).to_json()
        except NotFoundError as e:
            log.warning(e)
            return ApiGwResponse(404, cors=cors).to_json()
        except Exception as e:
            log.exception(e)
            return ApiGwResponse(500, cors=cors).to_json()
    
    return wrapper

