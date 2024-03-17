from curler import CLI
from pydantic import BaseModel


# Context is a Pydantic model that is used to store persistent state.
# Passed to each action as the `context` parameter.
class Context(BaseModel):
    access_token: str | None = None


# `base_url` is a parameter that is passed to every action.
# It can be overridden by the CLI with the `--base-url` option.
cli = CLI(Context(), base_url="https://httpbin.org")


# The `headers` function is a hook that is called before every request.
# It returns a dictionary of headers to be sent with the request.
# These are given to the `httpx.Client` constructor.
@cli.headers
def headers(context):
    if context.access_token is None:
        return {}
    return {"Authorization": f"Bearer {context.access_token}"}


# Calling `api` as a decorator registers the function as an available action.
# The function name is used as the action name for the CLI.
# The function signature is important, as it determines the parameter that
# can be passed to the function when it is called. The `client` and `context`
# parameters are always available. The rest are determined by extra parameters
# passed to the `API` constructor and CLI parameters.
#
# See `python examples/login.py login --help`
@cli
def login(client, context, base_url, token="123"):
    response = client.post(f"{base_url}/post", json={"access_token": token})
    response.raise_for_status()
    json = response.json()
    context.access_token = json["json"]["access_token"]
    return json


@cli
def bearer(client, context, base_url):
    print(f"{base_url}/bearer")
    response = client.get(f"{base_url}/bearer")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    cli.run()
