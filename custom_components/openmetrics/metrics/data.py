"""Data classes for metrics."""

from dataclasses import dataclass
from typing import Any


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
    model: str | None = None
    serial_number: str | None = None
    is_virtual: bool = False
    via_resource: str | None = None
    network_interfaces: set[str] | None = None
    filesystem_mountpoints: dict[str, Any] | None = None


@dataclass
class MetadataData:
    """Metadata for metrics providers."""

    provider_info: ProviderInfoData
    resources: dict[str, ResourceInfoData]
    available_metrics: list[str]
