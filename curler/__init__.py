from typing import Sequence, TypeVar, Generic, Callable, Any
from pydantic import BaseModel, ValidationError
import httpx
import argparse
import inspect


Context = TypeVar("Context", bound=BaseModel)
Endpoint = Callable[..., Any]
HeaderFn = Callable[..., dict[str, str]]


def json_output(result: Any):
    import json

    try:
        print(json.dumps(result, indent=2))
    except TypeError:
        print(result)


class CLI(Generic[Context]):
    _actions: dict[str, Endpoint]
    _context: Context
    _kwargs: dict[str, Any]
    _output_result: Callable[[Any], None]
    _header_fn: HeaderFn | None = None

    def __init__(self, context: Context, **kwargs):
        self._actions = {}
        self._context = context
        self._kwargs = kwargs
        self._output_result = json_output

    def perform(self, name: str, user_args: dict = {}) -> Any:
        endpoint = self._actions[name]
        assert endpoint is not None, "Endpoint not found."

        new_context = self.context()
        client = httpx.Client(headers=self._make_headers(user_args))

        args = user_args.copy()
        args["client"] = client
        args["context"] = new_context

        signature = inspect.signature(endpoint)

        arguments = {}
        for name, param in signature.parameters.items():
            if param.default is not inspect.Parameter.empty:
                arguments[name] = param.default
            if name in self._kwargs:
                arguments[name] = self._kwargs[name]
            if name in args:
                arguments[name] = args[name]

        result = endpoint(**arguments)

        if new_context != self._context:
            self._context = new_context
        return result

    def _make_headers(self, user_args: dict) -> dict[str, str]:
        if self._header_fn is None:
            return {}

        args = user_args.copy()
        args["context"] = self.context()

        signature = inspect.signature(self._header_fn)

        arguments = {}
        for name, param in signature.parameters.items():
            if param.default is not inspect.Parameter.empty:
                arguments[name] = param.default
            if name in self._kwargs:
                arguments[name] = self._kwargs[name]
            if name in args:
                arguments[name] = args[name]

        return self._header_fn(**arguments)

    def context(self) -> Context:
        return self._context.model_copy(deep=True)

    def __call__(self, endpoint: Endpoint) -> Endpoint:
        self._actions[endpoint.__name__] = endpoint

        # Check the endpoint takes the right arguments
        signature = inspect.signature(endpoint)
        assert (
            "client" in signature.parameters
        ), "Endpoint must take a `client` argument."
        assert (
            "context" in signature.parameters
        ), "Endpoint must take a `context` argument."

        return endpoint

    def headers(self, header_fn: HeaderFn) -> HeaderFn:
        self._header_fn = header_fn
        return header_fn

    def output(self, fn: Callable[[Any], None]) -> Callable[[Any], None]:
        self._output_result = fn
        return fn

    def _parser(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparsers = parser.add_subparsers(dest="action")

        if self._header_fn is not None:
            signature = inspect.signature(self._header_fn)
            header_params = list(signature.parameters.items())
        else:
            header_params = []

        for name, endpoint in self._actions.items():
            subparser = subparsers.add_parser(name)
            signature = inspect.signature(endpoint)

            all_params = list(signature.parameters.items())
            for name, param in header_params:
                if name not in all_params:
                    all_params.append((name, param))

            for name, param in all_params:
                if name in ["client", "context"]:
                    continue

                display_name = name.replace("_", "-")

                if param.default is not inspect.Parameter.empty:
                    help = f"Default: {param.default}"
                    required = False
                elif name in self._kwargs:
                    help = f"Default: {self._kwargs[name]}"
                    required = False
                else:
                    help = "Required"
                    required = True

                subparser.add_argument(
                    f"--{display_name}", required=required, help=help, dest=name
                )

        parser.add_argument(
            "--context",
            default=".context.json",
            help="Path to context file",
        )

        return parser

    def run(self, args: Sequence[str] | None = None) -> Any:
        parser = self._parser()
        params = parser.parse_args(args)

        if params.action is None:
            parser.print_help()
            return

        args_dict = vars(params)
        action = args_dict.pop("action")
        context_path = args_dict.pop("context")

        args_dict = {k: v for k, v in args_dict.items() if v is not None}

        self._load_context(context_path)
        result = self.perform(action, args_dict)
        self._save_context(context_path)

        self._output_result(result)

        return result

    def _load_context(self, path: str):
        try:
            with open(path, "r") as f:
                self._context = self._context.model_validate_json(f.read())
        except FileNotFoundError:
            print("No context file found, using default context.")
        except ValidationError:
            print("Invalid context file.")
            print("Continue with default context?")
            if input("y/n: ") != "y":
                exit()

    def _save_context(self, path: str):
        with open(path, "w") as f:
            f.write(self._context.model_dump_json())
