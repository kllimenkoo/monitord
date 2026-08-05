from fastapi import FastAPI

from schemas import CpuResponse, DiskResponse, NetResponse, RamResponse
from storage import read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

app = FastAPI()

@app.get('/cpu')
async def get_cpu() -> list[CpuResponse]:
    rows = await read_cpu_recent(limit=60)
    result = [CpuResponse(timestamp=row['timestamp'], usage_percentage=row['usage_percentage']) for row in rows]
    return result


@app.get('/ram')
async def get_ram() -> list[RamResponse]:
    rows = await read_ram_recent(limit=60)
    result = [RamResponse(
        timestamp=row['timestamp'],
        mem_usage_percentage=row['mem_usage_percentage'],
        swap_usage_percentage=row['swap_usage_percentage']) for row in rows]
    return result


@app.get('/disk/{device}')
async def get_disk(device: str) -> list[DiskResponse]:
    rows = await read_disk_recent(device=device, limit=60)
    result = [DiskResponse(
        timestamp=row['timestamp'],
        device=row['device'],
        read_iops=row['read_iops'],
        read_bytes_per_sec=row['read_bytes_per_sec'],
        write_iops=row['write_iops'],
        write_bytes_per_sec=row['write_bytes_per_sec'],
        io_utilization_percentage=row['io_utilization_percentage']) for row in rows]
    return result
