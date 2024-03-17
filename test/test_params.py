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
    def headers(context, header_param="default"):
        return {"header": header_param}

    @api
    def has_required_param(client, context, required_param):
        return required_param

    @api
    def has_optional_param(client, context, optional_param="default"):
        return optional_param

    @api
    def returns_header(client, context):
        return client.headers["header"]

    return api


def test_required_param_missing(api):
    try:
        api.run(["has_required_param"])
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 2


def test_required_param_provided(api):
    assert api.run(["has_required_param", "--required-param", "value"]) == "value"


def test_optional_param_missing(api):
    assert api.run(["has_optional_param"]) == "default"


def test_optional_param_provided(api):
    assert api.run(["has_optional_param", "--optional-param", "value"]) == "value"


def test_headers(api):
    assert api.run(["returns_header", "--header-param", "value"]) == "value"
