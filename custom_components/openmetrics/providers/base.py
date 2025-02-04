"""Base class for metrics providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..lib.metrics_core import Metric
from ..metrics import MetricFilter
from ..metrics.data import MetadataData, ProviderInfoData


@dataclass
class ProviderConfig:
    """Configuration for a metrics provider."""

    identifier_metric: str
    resource_identifier: str
    version_label: str
    metric_filters: list[MetricFilter]
    resource_type: str
    provider_name: str


class MetricsProvider(ABC):
    """Base class for metrics providers."""

    def __init__(self):
        """Initialize metrics provider."""
        self._metadata = MetadataData(
            provider_info=ProviderInfoData(
                name=self.get_config().provider_name,
                type=self.get_config().resource_type,
                version=None,
            ),
            resources=[],
            available_metrics=[],
        )

    @abstractmethod
    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        raise NotImplementedError

    @abstractmethod
    def extract_provider_info(self, family: Metric) -> dict | None:
        """Extract provider information from metric family."""
        raise NotImplementedError

    @abstractmethod
    def extract_resource_info(self, family: Metric) -> dict | None:
        """Extract resource information from metric family."""
        raise NotImplementedError

    @abstractmethod
    def extract_available_metrics(self, family: Metric) -> list[str] | None:
        """Extract available metrics from metric family."""
        raise NotImplementedError

    def get_metadata(self) -> MetadataData:
        """Return collected metadata."""
        return self._metadata
