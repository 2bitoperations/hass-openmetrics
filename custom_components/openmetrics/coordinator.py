"""Coordinator for OpenMetrics."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.openmetrics.metrics.data import ResourceInfoData

from .client import (
    CannotConnectError,
    ClientError,
    InvalidAuthError,
    OpenMetricsClient,
    RequestError,
)
from .const import (
    CONF_CUSTOM_METRIC_GROUP_BY,
    CONF_CUSTOM_METRIC_ID,
    CONF_CUSTOM_METRIC_NAME,
    CONF_CUSTOM_METRIC_QUERY,
    CONF_CUSTOM_METRIC_RESOURCE,
    CUSTOM_METRIC_DATA_PREFIX,
    DOMAIN,
)
from .custom_metrics import (
    compute_fingerprint,
    extract_custom_metric_value,
    find_matching_samples,
    parse_metric_query,
)

_LOGGER = logging.getLogger(__name__)


class OpenMetricsDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to manage OpenMetrics data update coordination."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenMetricsClient,
        resources: dict[str, ResourceInfoData],
        update_interval: int,
        custom_metrics: list[dict] | None = None,
    ) -> None:
        """Initialize the data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._client = client
        self.resources = resources
        self.network_interfaces = None
        self.custom_metrics: list[dict] = custom_metrics or []
        # Labels discovered per custom-metric-id → fingerprint → label dict
        # (used by the wildcard sensor listener in sensor.py)
        self.custom_metric_labels: dict[str, dict[str, dict[str, str]]] = {}
        # Fingerprints that have already been turned into HA entities
        self.registered_custom_fingerprints: dict[str, set[str]] = {}

    async def _async_update_data(self):
        """Fetch OpenMetrics data."""
        try:
            _LOGGER.debug(
                "Started fetching %s data from %s", self.name, self._client.url
            )
            # Fetch once; get both processed metrics and raw families for custom metrics
            metrics, families = await self._client.get_all_data(
                list(self.resources.keys())
            )
            sensor_data = self._client.process_metrics(metrics, self.update_interval)
            # Overlay custom metric values
            for cm in self.custom_metrics:
                resource = cm.get(CONF_CUSTOM_METRIC_RESOURCE)
                if not resource:
                    continue
                cm_id = cm[CONF_CUSTOM_METRIC_ID]
                group_by: list[str] = cm.get(CONF_CUSTOM_METRIC_GROUP_BY) or []
                try:
                    metric_name, filters = parse_metric_query(cm[CONF_CUSTOM_METRIC_QUERY])
                    if group_by:
                        # Multi-value: one data key per fingerprint
                        matches = find_matching_samples(families, metric_name, filters)
                        if cm_id not in self.custom_metric_labels:
                            self.custom_metric_labels[cm_id] = {}
                        for value, sample_labels in matches:
                            fp = compute_fingerprint(sample_labels, group_by)
                            self.custom_metric_labels[cm_id][fp] = sample_labels
                            if resource not in sensor_data:
                                sensor_data[resource] = {}
                            data_key = f"{CUSTOM_METRIC_DATA_PREFIX}{cm_id}__{fp}"
                            sensor_data[resource][data_key] = value
                    else:
                        # Single-value: first match
                        if resource not in sensor_data:
                            sensor_data[resource] = {}
                        value = extract_custom_metric_value(families, metric_name, filters)
                        data_key = CUSTOM_METRIC_DATA_PREFIX + cm_id
                        sensor_data[resource][data_key] = value
                except (ValueError, KeyError) as e:
                    _LOGGER.warning(
                        "Failed to extract custom metric '%s': %s",
                        cm.get(CONF_CUSTOM_METRIC_NAME),
                        e,
                    )
        except CannotConnectError as e:
            _LOGGER.error("Failed to connect: %s", str(e))
        except InvalidAuthError as e:
            _LOGGER.error("Authentication failed: %s", str(e))
        except RequestError as e:
            _LOGGER.error("Resources error: %s", str(e))
        except ClientError as e:
            _LOGGER.error("Processing error: %s", str(e))
        except ValueError as e:
            _LOGGER.error("Value error: %s", str(e))
        except Exception:
            _LOGGER.exception("Unexpected exception")
        else:
            return sensor_data
