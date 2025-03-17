"""Registry for provider configurations."""

from custom_components.openmetrics.providers.generic import GenericProvider

from .base import MetricsProvider
from .cadvisor import CADVISOR_VERSION_INFO, CadvisorProvider
from .node_exporter import NODE_EXPORTER_BUILD_INFO, NodeExporterProvider


class ProviderRegistry:
    """Registry for provider configurations."""

    def __init__(self):
        """Initialize provider registry."""
        self.providers = {
            NODE_EXPORTER_BUILD_INFO: NodeExporterProvider(),
            CADVISOR_VERSION_INFO: CadvisorProvider(),
        }
        self.__default_provider = GenericProvider()

    def get_provider(self, identifier_metric: str) -> MetricsProvider | None:
        """Get provider based on identifier metric."""
        return self.providers.get(identifier_metric)

    def get_default_provider(self) -> MetricsProvider:
        """Get default provider."""
        return self.__default_provider
