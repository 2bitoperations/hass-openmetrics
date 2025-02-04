"""Registry for provider configurations."""

from ..const import (
    CADVISOR_VERSION_INFO,
    NODE_EXPORTER_BUILD_INFO,
)
from .base import MetricsProvider
from .cadvisor import CadvisorProvider
from .node_exporter import NodeExporterProvider


class ProviderRegistry:
    """Registry for provider configurations."""

    def __init__(self):
        """Initialize provider registry."""
        self.providers = {
            NODE_EXPORTER_BUILD_INFO: NodeExporterProvider(),
            CADVISOR_VERSION_INFO: CadvisorProvider(),
        }

    def get_provider(self, identifier_metric: str) -> MetricsProvider | None:
        """Get provider based on identifier metric."""
        return self.providers.get(identifier_metric)
