import asyncio

import uvicorn

from monitord.anomaly import run_anomaly_checks
from monitord.api import app as fastapi_app
from monitord.compute import (
    compute_cpu_metrics,
    compute_disk_metrics,
    compute_net_metrics,
    compute_ram_metrics,
)
from monitord.readers import (
    read_cpu_stats,
    read_disk_stats,
    read_net_stats,
    read_ram_stats,
)
from monitord.storage import init_db, write_cpu, write_disk, write_net, write_ram

INTERVAL: float = 2.0


async def cpu_collector() -> None:
    prev = read_cpu_stats()

    while True:
        await asyncio.sleep(INTERVAL)
        curr = read_cpu_stats()
        metrics = compute_cpu_metrics(prev, curr)
        if metrics is not None:
            await write_cpu(metrics)
        prev = curr


async def ram_collector() -> None:
    while True:
        await asyncio.sleep(INTERVAL)
        snapshot = read_ram_stats()
        metrics = compute_ram_metrics(snapshot)
        await write_ram(metrics)


async def disk_collector() -> None:
    prev = read_disk_stats()

    while True:
        await asyncio.sleep(INTERVAL)
        curr = read_disk_stats()
        metrics = compute_disk_metrics(prev, curr, INTERVAL)
        await write_disk(metrics)
        prev = curr


async def net_collector() -> None:
    prev = read_net_stats()

    while True:
        await asyncio.sleep(INTERVAL)
        curr = read_net_stats()
        metrics = compute_net_metrics(prev, curr, INTERVAL)
        await write_net(metrics)
        prev = curr


async def main():
    await init_db()
    config = uvicorn.Config(
        fastapi_app,
        host='127.0.0.1',
        port=8000,
        log_level='warning',
    )
    server = uvicorn.Server(config)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(cpu_collector())
        tg.create_task(ram_collector())
        tg.create_task(disk_collector())
        tg.create_task(net_collector())
        tg.create_task(run_anomaly_checks())
        tg.create_task(server.serve())


if __name__ == '__main__':
    asyncio.run(main())
