"""Data classes for metrics."""

from dataclasses import dataclass


@dataclass
class ProviderInfoData:
    """Provider information data."""

    name: str
    type: str
    version: str | None = None


@dataclass
class ResourceInfoData:
    """Resource information data."""

    type: str
    name: str | None = None
    software: str | None = None
    version: str | None = None


@dataclass
class MetadataData:
    """Metadata for metrics providers."""

    provider_info: ProviderInfoData
    resources: list[ResourceInfoData]
    available_metrics: list[str]
