from pydantic import BaseModel


class CpuResponse(BaseModel):
    timestamp: float
    usage_percentage: float


class RamResponse(BaseModel):
    timestamp: float
    mem_usage_percentage: float
    swap_usage_percentage: float


class DiskResponse(BaseModel):
    timestamp: float
    device: str
    read_iops: float
    read_bytes_per_sec: float
    write_iops: float
    write_bytes_per_sec: float
    io_utilization_percentage: float


class NetResponse(BaseModel):
    timestamp: float
    interface: str
    receive_bytes_per_sec: float
    receive_packets_per_sec: float
    transmit_bytes_per_sec: float
    transmit_packets_per_sec: float
    receive_packet_error_count: float
    receive_packet_drop_count: float
    transmit_packet_error_count: float
    transmit_packet_drop_count: float
