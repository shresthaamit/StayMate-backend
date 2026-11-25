
from .providers import get_call_provider


def execute_hotel_call(call):
    """
    Execute a hotel call through its configured provider.

    The workflow selects the provider without needing to know
    the internal details of how that provider operates.
    """

    provider = get_call_provider(call.mode)

    return provider.execute(call)
