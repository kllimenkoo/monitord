from typing import NamedTuple


class RamRawData(NamedTuple):
    """Holds raw data read from /proc/meminfo."""
    mem_total: int
    mem_available: int
    swap_total: int
    swap_free: int


class DiskRawData(NamedTuple):
    """Holds raw data read from /proc/diskstats."""
    reads_completed: int
    sectors_read: int
    writes_completed: int
    sectors_written: int
    io_time_spent: int


class DiskMetrics(NamedTuple):
    """Holds calculated data from disk read."""
    read_iops: float
    read_bytes_per_sec: float
    write_iops: float
    write_bytes_per_sec: float
    io_utilization_percent: float


class NetRawData(NamedTuple):
    """Holds raw data read from /proc/net/dev."""
    receive_bytes: int
    receive_packets: int
    receive_errors: int
    receive_drops: int
    transmit_bytes: int
    transmit_packets: int
    transmit_errors: int
    transmit_drops: int


class NetMetrics(NamedTuple):
    """Holds calculated data from network read."""
    receive_bytes_per_sec: float
    receive_packets_per_sec: float
    transmit_bytes_per_sec: float
    transmit_packets_per_sec: float
    receive_packet_error_count: float
    receive_packet_drop_count: float
    transmit_packet_error_count: float
    transmit_packet_drop_count: float
