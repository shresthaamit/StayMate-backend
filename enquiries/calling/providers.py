
from abc import ABC, abstractmethod


class BaseCallProvider(ABC):
    """
    Common interface for all StayMate call providers.

    Future providers can implement this interface for
    real telephone calls.
    """

    @abstractmethod
    def execute(self, call):
        """Execute a hotel call and return the updated call."""
        raise NotImplementedError


class SimulatedCallProvider(BaseCallProvider):
    """
    Executes calls using StayMate's existing simulation service.

    No telephone call is made.
    """

    def execute(self, call):
        # Import locally to avoid circular imports.
        from enquiries.services import run_simulated_hotel_call

        return run_simulated_hotel_call(call)


def get_call_provider(mode):
    """
    Return the provider responsible for the requested call mode.
    """

    if mode == "simulated":
        return SimulatedCallProvider()

    raise ValueError(
        f"Unsupported call mode: {mode}"
    )
