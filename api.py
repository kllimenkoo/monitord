from fastapi import FastAPI

from schemas import CpuResponse, DiskResponse, NetResponse, RamResponse
from storage import read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

app = FastAPI()

@app.get('/cpu')
async def get_cpu() -> list[CpuResponse]:
    rows = await read_cpu_recent(limit=60)
    result = [CpuResponse(timestamp=row['timestamp'], usage_percentage=row['usage_percentage']) for row in rows]
    return result
