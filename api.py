from fastapi import FastAPI

from schemas import CpuResponse, DiskResponse, NetResponse, RamResponse
from storage import read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

app = FastAPI()


@app.get('/get_device_names')
async def get_device_names() -> list[str]:
    result = await get_known_devices()
    return result


@app.get('/get_interface_names')
async def get_interface_names() -> list[str]:
    result = await get_known_interfaces()
    return result


@app.get('/cpu')
async def get_cpu(limit: int = 60) -> list[CpuResponse]:
    rows = await read_cpu_recent(limit=limit)
    result = [
        CpuResponse(
            timestamp=row['timestamp'], usage_percentage=row['usage_percentage']
        )
        for row in rows
    ]
    return result


@app.get('/ram')
async def get_ram(limit: int = 60) -> list[RamResponse]:
    rows = await read_ram_recent(limit=limit)
    result = [
        RamResponse(
            timestamp=row['timestamp'],
            mem_usage_percentage=row['mem_usage_percentage'],
            swap_usage_percentage=row['swap_usage_percentage'],
        )
        for row in rows
    ]
    return result


@app.get('/disk/{device}')
async def get_disk(device: str, limit: int = 60) -> list[DiskResponse]:
    rows = await read_disk_recent(device=device, limit=limit)
    result = [
        DiskResponse(
            timestamp=row['timestamp'],
            device=row['device'],
            read_iops=row['read_iops'],
            read_bytes_per_sec=row['read_bytes_per_sec'],
            write_iops=row['write_iops'],
            write_bytes_per_sec=row['write_bytes_per_sec'],
            io_utilization_percentage=row['io_utilization_percentage'],
        )
        for row in rows
    ]
    return result


@app.get('/net/{interface}')
async def get_interface(interface: str, limit: int = 60) -> list[NetResponse]:
    rows = await read_net_recent(interface=interface, limit=limit)
    result = [
        NetResponse(
            timestamp=row['timestamp'],
            interface=row['interface'],
            receive_bytes_per_sec=row['receive_bytes_per_sec'],
            receive_packets_per_sec=row['receive_packets_per_sec'],
            transmit_bytes_per_sec=row['transmit_bytes_per_sec'],
            transmit_packets_per_sec=row['transmit_packets_per_sec'],
            receive_packet_error_count=row['receive_packet_error_count'],
            receive_packet_drop_count=row['receive_packet_drop_count'],
            transmit_packet_error_count=row['transmit_packet_error_count'],
            transmit_packet_drop_count=row['transmit_packet_drop_count'],
        )
        for row in rows
    ]
    return result
