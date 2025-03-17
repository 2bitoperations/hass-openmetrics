"""Constants for the openmetrics integration."""

DOMAIN = "openmetrics"

CONF_RESOURCES = "resources"
CONF_METRICS = "metrics"

CONTENT_TYPE_OPENMETRICS = "application/openmetrics-text"
CONTENT_TYPE_TEXT = "text/plain"

PROVIDER_NAME_GENERIC = "Generic"
PROVIDER_NAME_NODE_EXPORTER = "Node Exporter"
PROVIDER_NAME_CADVISOR = "cAdvisor"
PROVIDER_TYPE_NODE = "node"
PROVIDER_TYPE_NODE_VIRTUAL = "virtual_node"
PROVIDER_TYPE_CONTAINER = "container"
RESOURCE_TYPE_GENERIC = "generic"
RESOURCE_TYPE_NODE = PROVIDER_TYPE_NODE
RESOURCE_TYPE_CONTAINER = PROVIDER_TYPE_CONTAINER

DEFAULT_SCAN_INTERVAL = 10

METRIC_UPTIME_SECONDS = "uptime_seconds"
METRIC_CPU_TEMP = "cpu_temp_celsius"
METRIC_CPU_USAGE_PCT = "cpu_usage_pct"
METRIC_MEMORY_USAGE_BYTES = "memory_usage_bytes"
METRIC_MEMORY_USAGE_PCT = "memory_usage_pct"
METRIC_DISK_USAGE_BYTES = "disk_usage_bytes"
METRIC_DISK_USAGE_PCT = "disk_usage_pct"
METRIC_NETWORK_RECEIVE_BYTES = "network_receive_bytes"
METRIC_NETWORK_TRANSMIT_BYTES = "network_transmit_bytes"
METRIC_DEVICE_NAME = "device_name"
# Node Exporter textfile collector metrics
METRIC_CONTAINER_STATUS = "container_status"
METRIC_CONTAINER_STATUS_CREATED = "container_status_created"
METRIC_CONTAINER_STATUS_RUNNING = "container_status_running"
METRIC_CONTAINER_STATUS_PAUSED = "container_status_paused"
METRIC_CONTAINER_STATUS_RESTARTING = "container_status_restarting"
METRIC_CONTAINER_STATUS_REMOVING = "container_status_removing"
METRIC_CONTAINER_STATUS_EXITED = "container_status_exited"
METRIC_CONTAINER_STATUS_DEAD = "container_status_dead"
METRIC_CONTAINER_UPTIME = "container_uptime"

PROPERTY_DEVICE_MODEL = "device_model"
PROPERTY_DEVICE_SERIAL = "device_serial"
PROPERTY_DEVICE_SOFTWARE = "device_software"
PROPERTY_DEVICE_VERSION = "device_version"
PROPERTY_LAST_START_TIME = "last_start_time"
PROPERTY_CPU_CORES = "cpu_cores"
PROPERTY_MEMORY_SIZE = "memory_size"
PROPERTY_DISK_SIZE = "disk_size"
