"""Constants for the openmetrics integration."""

DOMAIN = "openmetrics"

CONF_RESOURCES = "resources"
CONF_METRICS = "metrics"

PROVIDER_NAME_NODE_EXPORTER = "Node exporter"
PROVIDER_NAME_CADVISOR = "cAdvisor"
PROVIDER_TYPE_NODE = "node"
PROVIDER_TYPE_CONTAINER = "container"

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

PROPERTY_LAST_START_TIME = "last_start_time"
PROPERTY_CPU_CORES = "cpu_cores"
PROPERTY_MEMORY_SIZE = "memory_size"
PROPERTY_DISK_SIZE = "disk_size"

NODE_EXPORTER_BUILD_INFO = "node_exporter_build_info"
NODE_UNAME_INFO = "node_uname_info"
NODE_OS_INFO = "node_os_info"
NODE_TIME = "node_time_seconds"
NODE_BOOT_TIME = "node_boot_time_seconds"
NODE_HWMON_TEMP = "node_hwmon_temp_celsius"
NODE_CPU_TEMP = "node_thermal_zone_temp"
NODE_CPU_IDLE_SECONDS = "node_cpu_seconds"
NODE_MEMORY_FREE = "node_memory_MemFree_bytes"
NODE_MEMORY_TOTAL = "node_memory_MemTotal_bytes"
NODE_MEMORY_SWAP_TOTAL = "node_memory_SwapTotal_bytes"
NODE_FILESYSTEM_SIZE = "node_filesystem_size_bytes"
NODE_FILESYSTEM_FREE = "node_filesystem_free_bytes"
NODE_NETWORK_RECEIVE = "node_network_receive_bytes"
NODE_NETWORK_TRANSMIT = "node_network_transmit_bytes"

CADVISOR_VERSION_INFO = "cadvisor_version_info"
MACHINE_CPU_CORES = "machine_cpu_cores"
MACHINE_MEMORY = "machine_memory_bytes"
MACHINE_SWAP = "machine_swap_bytes"
CONTAINER_START_TIME = "container_start_time_seconds"
CONTAINER_CPU_USAGE = "container_cpu_usage_seconds"
CONTAINER_MEMORY_LIMIT = "container_spec_memory_limit_bytes"
CONTAINER_MEMORY_USAGE = "container_memory_usage_bytes"
CONTAIENR_MEMORY_SWAP = "container_memory_swap"
CONTAINER_FS_USAGE = "container_fs_usage_bytes"
CONTAINER_FS_LIMIT = "container_fs_limit_bytes"
CONTAINER_NETWORK_RECEIVE = "container_network_receive_bytes"
CONTAINER_NETWORK_TRANSMIT = "container_network_transmit_bytes"
