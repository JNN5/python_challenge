# Python Challenge
## Tasks
1. Read through the existing code and try to understand it
2. Implement the following Requirement by reusing patterns and code from the existing code
## Requirement
### Context
- a bag has the following attributes:
  - id
  - color
  - weight in grams
### Given
- bags of various colors and weights
### When
- a user submits bag data
### Then
- the bag data (as defined in context) is saved to DynamoDB

## Hints
- Start by creating a python virtual environment (python3 -m venv .venv && source .venv/bin/activate)
- Install all packages (pip install -r requirements.txt)
- You can run the tests with this command: python -m pytest tests/
- The repo uses a wrapper package to interact with DynamoDB called pynamodb. An example of a pynamo model can be found under src/layer_diva/python/models/example_booking.py
- we want to be able to verify your code works
- your code will run in a lambda function that is triggered by an API gateway (just like the example_get_request under src/functions/lambda_function.py)

- please prepare to walk through your code