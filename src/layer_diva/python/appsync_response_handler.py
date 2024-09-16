from aws_lambda_powertools import Logger
log = Logger()
def appsync_response_handler(func):
    def wrap(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return {"data": result, "error": None}
        except Exception as e:
            log.exception("An error occurred: %s", str(e))
            return {"data": None, "error": str(e)}

    return wrap