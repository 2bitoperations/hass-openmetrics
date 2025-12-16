"""Config flow for openmetrics integration."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .client import (
    CannotConnectError,
    ClientError,
    InvalidAuthError,
    OpenMetricsClient,
    RequestError,
)
from .const import (
    CONF_METRICS,
    CONF_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .metrics.data import MetadataData
from .metrics.processor import MetricsError, ResourcesError
from .options_flow import OpenMetricsOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=vol.Coerce(bool)(False)): bool,
    }
)


class OpenMetricsConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openmetrics."""

    VERSION = 3
    title: str
    data: dict[str, Any]
    metadata: MetadataData
    provider_name: str

    def _get_available_resources(self) -> list[str]:
        """Get available resources from the metadata."""
        return [
            resource.name
            for resource in self.metadata.resources.values()
            if resource.name and not resource.is_virtual
        ]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        # Process user input if provided
        if user_input is not None:
            try:
                # Check if an entry already exists with the same host
                for entry in self._async_current_entries():
                    if entry.data[CONF_URL] == user_input[CONF_URL]:
                        return self.async_abort(reason="already_configured")
                # Validate input
                self.data, self.metadata = await self._async_validate_user_step_input(
                    user_input
                )
                # Extract provider info
                provider_name = self.metadata.provider_info.name
                # Define entry title
                host = urllib.parse.urlparse(user_input[CONF_URL]).netloc
                self.title = host
                if provider_name:
                    self.title += f" ({provider_name})"
                # Show resources form
                return await self.async_step_resources()
            except CannotConnectError as e:
                _LOGGER.error("Failed to connect: %s", str(e))
                errors["base"] = "cannot_connect"
            except InvalidAuthError as e:
                _LOGGER.error("Authentication failed: %s", str(e))
                errors["base"] = "invalid_auth"
            except RequestError as e:
                _LOGGER.error("Request error: %s", str(e))
                errors["base"] = "request_error"
            except ClientError as e:
                _LOGGER.error("Processing error: %s", str(e))
                errors["base"] = "processing_error"
            except ResourcesError as e:
                _LOGGER.error("Resources error: %s", str(e))
                errors["base"] = "no_resources"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            last_step=False,
        )

    async def _async_validate_user_step_input(self, data: dict[str, Any]) -> tuple:
        """Process user input and create new or update existing config entry."""
        try:
            url = data[CONF_URL]
            username = data.get(CONF_USERNAME)
            password = data.get(CONF_PASSWORD)
            verify_ssl = data[CONF_VERIFY_SSL]
            # Create client
            client = OpenMetricsClient(url, verify_ssl, username, password)
            # Get metadata
            metadata = await client.get_metadata()
            # # Check if resources are available
            if len(metadata.resources) == 0:
                raise ResourcesError("No resources available")
            # Define scan interval
            data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
        except aiohttp.ClientError as e:
            raise e from CannotConnectError
        else:
            return (data, metadata)

    async def async_step_resources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the resources definition step."""
        errors: dict[str, str] = {}
        available_resources = self._get_available_resources()
        selected = available_resources
        # Process user input if provided
        if user_input is not None:
            try:
                # Validate input
                config_input = self._validate_resources_step_input(user_input)
                # Set entry data
                self.data[CONF_RESOURCES] = config_input[CONF_RESOURCES]
                # Show metrics form
                return await self.async_step_metrics()
            except ResourcesError as e:
                _LOGGER.error("Resources error: %s", str(e))
                errors["base"] = "no_resources"
            except ValueError as e:
                _LOGGER.error("Invalid input: %s", str(e))
                errors["base"] = "invalid_input"
            finally:
                selected = user_input.get(CONF_RESOURCES, [])
        # Define data schema
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_RESOURCES,
                    description={"suggested_value": selected},
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=available_resources,
                        translation_key=CONF_RESOURCES,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            },
            extra=vol.ALLOW_EXTRA,
        )
        # Show form
        return self.async_show_form(
            step_id="resources", data_schema=data_schema, errors=errors, last_step=False
        )

    def _validate_resources_step_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process user input and create new or update existing config entry."""
        resources = data[CONF_RESOURCES]
        if len(resources) == 0:
            raise ResourcesError("No resources selected")
        return {
            CONF_RESOURCES: resources,
        }

    async def async_step_metrics(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the metrics definition step."""
        errors: dict[str, str] = {}
        available_metrics = self.metadata.available_metrics
        selected = available_metrics
        # Process user input if provided
        if user_input is not None:
            try:
                # Validate input
                config_input = self._validate_metrics_step_input(user_input)
                # Set entry data
                metrics = []
                for metric in available_metrics:
                    if metric in config_input[CONF_METRICS]:
                        if metric not in metrics:
                            metrics.append(metric)
                self.data[CONF_METRICS] = metrics
                # Create entry
                return self.async_create_entry(title=self.title, data=self.data)
            except MetricsError as e:
                _LOGGER.error("Metrics error: %s", str(e))
                errors["base"] = "no_metrics"
            except ValueError as e:
                _LOGGER.error("Invalid input: %s", str(e))
                errors["base"] = "invalid_input"
            finally:
                selected = user_input.get(CONF_METRICS, [])
        # Define data schema
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_METRICS,
                    description={"suggested_value": selected},
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=available_metrics,
                        translation_key=CONF_METRICS,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            },
            extra=vol.ALLOW_EXTRA,
        )
        # Show form
        return self.async_show_form(
            step_id="metrics", data_schema=data_schema, errors=errors, last_step=True
        )

    def _validate_metrics_step_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process user input and create new or update existing config entry."""
        metrics = data[CONF_METRICS]
        if len(metrics) == 0:
            raise MetricsError("No metrics selected")
        return {
            CONF_METRICS: metrics,
        }

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OpenMetricsOptionsFlowHandler()
