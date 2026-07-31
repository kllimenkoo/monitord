import asyncio

from readers import read_cpu_stats, read_disk_stats, read_ram_stats, read_net_stats
from compute import compute_cpu_metrics, compute_disk_metrics, compute_net_metrics, compute_ram_metrics
from storage import init_db, write_cpu, write_ram, write_disk, write_net


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

