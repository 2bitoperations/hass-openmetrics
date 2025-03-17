"""Class for interacting with OpenMetrics."""

from datetime import timedelta
from http import HTTPStatus

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .const import CONTENT_TYPE_OPENMETRICS
from .metrics.data import MetadataData
from .metrics.processor import OpenMetricsProcessor


class RequestError(HomeAssistantError):
    """Error to indicate a client request error."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class ClientError(HomeAssistantError):
    """Base class for client errors."""


class OpenMetricsClient:
    """Class for interacting with OpenMetrics."""

    def __init__(
        self, url: str, verify_ssl: bool, username=None, password=None
    ) -> None:
        """Initialize the OpenMetrics client."""
        self.url = url
        self.verify_ssl = verify_ssl
        self.username = username
        self.password = password
        self.processor = OpenMetricsProcessor()

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: dict | None = None,
        data: dict | None = None,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request."""
        return await session.request(
            method, url, headers=headers, data=data, verify_ssl=self.verify_ssl
        )

    async def _async_request_data(self) -> tuple[str, str | None]:
        """Request data from metrics provider."""
        async with aiohttp.ClientSession() as session:
            # Define request headers
            headers = {"Accept": f"{CONTENT_TYPE_OPENMETRICS};charset=utf-8"}
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers["Authorization"] = auth.encode()
            # Make request
            try:
                response = await self._make_request(session, "GET", self.url, headers)
            except aiohttp.ClientConnectionError as e:
                raise CannotConnectError(str(e)) from e
            except aiohttp.ClientError as e:
                raise RequestError(str(e)) from e
            # Process response
            if response.status == HTTPStatus.OK.value:
                # Return response text and content type
                return (await response.text(), response.headers.get("Content-Type"))
            if response.status == HTTPStatus.UNAUTHORIZED.value:
                raise InvalidAuthError(f"Invalid auth for {self.url}")
            raise RequestError(
                f"Request failed with status code '{response.status}' and reason '{response.reason}'"
            )

    async def check_connection(self) -> bool:
        """Check connection to the metrics provider."""
        response_text, content_type = await self._async_request_data()
        if response_text and content_type:
            return True
        return False

    async def get_metadata(self) -> MetadataData:
        """Get metadata from a metrics provider."""
        response_text, content_type = await self._async_request_data()
        families = self.processor.parse_data(response_text, content_type)
        return self.processor.extract_metadata(families)

    async def get_metrics(self, resources: list[str]) -> dict:
        """Get metrics from a metrics provider."""
        response_text, content_type = await self._async_request_data()
        families = self.processor.parse_data(response_text, content_type)
        return self.processor.extract_metrics(families, resources)

    def process_metrics(self, metrics: dict, update_interval: timedelta | None) -> dict:
        """Process metrics."""
        if update_interval is None or update_interval.seconds <= 0:
            raise ValueError("Update interval must be positive")
        return self.processor.process_metrics(metrics, update_interval.seconds)
