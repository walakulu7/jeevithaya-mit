"""
Composition root for the service layer (Dependency Inversion).

Views ask this container for their collaborators instead of constructing
concrete services themselves. Tests or alternative deployments can swap an
implementation in one place, e.g. ``services.inventory = FakeInventoryService()``.
"""

from .services import InventoryService, RequestFulfillmentService


class ServiceContainer:
    """Builds and wires the application's domain services."""

    def __init__(self, inventory=None, requests=None):
        self.inventory = inventory or InventoryService()
        self.requests = requests or RequestFulfillmentService(inventory_service=self.inventory)


services = ServiceContainer()
