import httpx
from pydantic import BaseModel
import pytest

from .utils import CLI


class Context(BaseModel):
    access_token: str | None = None


@pytest.fixture
def api():
    api = CLI(Context())

    @api.headers
    def headers(context):
        if context.access_token is None:
            return {}
        return {"Authorization": f"Bearer {context.access_token}"}

    @api
    def login(client, context):
        response = client.post("https://httpbin.org/post", json={"access_token": "123"})
        response.raise_for_status()
        json = response.json()
        context.access_token = json["json"]["access_token"]
        return json

    @api
    def bearer(client, context):
        response = client.get("https://httpbin.org/bearer")
        response.raise_for_status()
        return response.json()

    return api


def test_bearer_fail(api):
    try:
        api.run(["bearer"])
        assert False, "Expected 401"
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 401


def test_login_and_bearer(api):
    api.run(["login"])
    response = api.run(["bearer"])
    assert response["token"] == "123"
