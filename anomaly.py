import asyncio
import logging
import statistics
from pathlib import Path

from storage import (
    get_known_devices,
    get_known_interfaces,
    read_cpu_recent,
    read_disk_recent,
    read_net_recent,
    read_ram_recent,
)

CPU_SHORT_WINDOW, CPU_LONG_WINDOW = 5, 20
CPU_SENSITIVITY = 2.0
CPU_STDEV_FLOOR = 0.5

RAM_SHORT_WINDOW, RAM_LONG_WINDOW = 5, 20
RAM_SENSITIVITY = 2.0
RAM_STDEV_FLOOR = 0.5

DISK_SHORT_WINDOW, DISK_LONG_WINDOW = 10, 20
DISK_SENSITIVITY = 2.0
DISK_STDEV_FLOOR = 0.5

NET_SHORT_WINDOW, NET_LONG_WINDOW = 8, 20
NET_SENSITIVITY = 2.0
NET_STDEV_FLOOR = 0.5

LOG_DIR = Path('/var/log/monitord')
LOG_FILE = LOG_DIR / 'anomaly.py'

LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILE,
    encoding='utf-8',
    level=logging.WARNING,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def log_anomaly(
    metric: str,
    device: str | None,
    avg_short: float,
    avg_long: float,
    threshold: float,
) -> None:
    logger.warning(
        f'ANOMALY {metric.upper()} device={device or "N/A"}'
        f'short_avg={avg_short:.1f} long_avg={avg_long:.1f} threshold={threshold:.1f}'
    )


async def check_cpu() -> None:
    long_window = await read_cpu_recent(limit=CPU_LONG_WINDOW)
    if len(long_window) < CPU_LONG_WINDOW:
        return None

    short_window = long_window[:CPU_SHORT_WINDOW]

    long_values = [m['usage_percentage'] for m in long_window]
    short_values = [m['usage_percentage'] for m in short_window]

    avg_long = statistics.mean(long_values)
    avg_short = statistics.mean(short_values)

    long_stdev = max(statistics.stdev(long_values), CPU_STDEV_FLOOR)
    adaptive_threshold = avg_long + (CPU_SENSITIVITY * long_stdev)

    if avg_short > 0:
        log_anomaly(
            metric='cpu',
            device=None,
            avg_short=avg_short,
            avg_long=avg_long,
            threshold=adaptive_threshold,
        )


async def check_ram() -> None:
    long_window = await read_ram_recent(limit=RAM_LONG_WINDOW)
    if len(long_window) < RAM_LONG_WINDOW:
        return None

    short_window = long_window[:RAM_SHORT_WINDOW]

    long_values_mem = [m['mem_usage_percentage'] for m in long_window]
    short_values_mem = [m['mem_usage_percentage'] for m in short_window]

    avg_long_mem = statistics.mean(long_values_mem)
    avg_short_mem = statistics.mean(short_values_mem)

    long_stdev_mem = max(statistics.stdev(long_values_mem), RAM_STDEV_FLOOR)
    adaptive_threshold_mem = avg_long_mem + (RAM_SENSITIVITY * long_stdev_mem)

    long_values_swap = [m['swap_usage_percentage'] for m in long_window]
    short_values_swap = [m['swap_usage_percentage'] for m in short_window]

    avg_long_swap = statistics.mean(long_values_swap)
    avg_short_swap = statistics.mean(short_values_swap)

    long_stdev_swap = max(statistics.stdev(long_values_swap), RAM_STDEV_FLOOR)
    adaptive_threshold_swap = avg_long_swap + (RAM_SENSITIVITY * long_stdev_swap)

    if avg_short_mem > adaptive_threshold_mem:
        log_anomaly(
            metric='ram',
            device=None,
            avg_short=avg_short_mem,
            avg_long=avg_long_mem,
            threshold=adaptive_threshold_mem,
        )

    if avg_short_swap > adaptive_threshold_swap:
        log_anomaly(
            metric='swap',
            device=None,
            avg_short=avg_short_swap,
            avg_long=avg_long_swap,
            threshold=adaptive_threshold_swap,
        )


async def check_disk() -> None:
    devices = await get_known_devices()
    for device in devices:
        long_window = await read_disk_recent(device=device, limit=DISK_LONG_WINDOW)
        if len(long_window) < DISK_LONG_WINDOW:
            continue

        short_window = long_window[:DISK_SHORT_WINDOW]

        long_values = [m['io_utilization_percentage'] for m in long_window]
        short_values = [m['io_utilization_percentage'] for m in short_window]

        avg_long = statistics.mean(long_values)
        avg_short = statistics.mean(short_values)

        long_stdev = max(statistics.stdev(long_values), DISK_STDEV_FLOOR)
        adaptive_threshold = avg_long + (DISK_SENSITIVITY * long_stdev)

        if avg_short > adaptive_threshold:
            log_anomaly(
                metric='disk',
                device=device,
                avg_short=avg_short,
                avg_long=avg_long,
                threshold=adaptive_threshold,
            )


async def check_net() -> None:
    interfaces = await get_known_interfaces()
    for interface in interfaces:
        long_window = await read_net_recent(interface=interface, limit=NET_LONG_WINDOW)
        if len(long_window) < NET_LONG_WINDOW:
            continue

        short_window = long_window[:NET_SHORT_WINDOW]

        long_values_receive = [m['receive_bytes_per_sec'] for m in long_window]
        short_values_receive = [m['receive_bytes_per_sec'] for m in short_window]

        avg_long_receive = statistics.mean(long_values_receive)
        avg_short_receive = statistics.mean(short_values_receive)

        long_stdev_receive = max(statistics.stdev(long_values_receive), NET_STDEV_FLOOR)
        adaptive_threshold_receive = avg_long_receive + (
            NET_SENSITIVITY * long_stdev_receive
        )

        long_values_transmit = [m['transmit_bytes_per_sec'] for m in long_window]
        short_values_transmit = [m['transmit_bytes_per_sec'] for m in short_window]

        avg_long_transmit = statistics.mean(long_values_transmit)
        avg_short_transmit = statistics.mean(short_values_transmit)

        long_stdev_transmit = max(
            statistics.stdev(long_values_transmit), NET_STDEV_FLOOR
        )
        adaptive_threshold_transmit = avg_long_transmit + (
            NET_SENSITIVITY * long_stdev_transmit
        )

        if avg_short_receive > adaptive_threshold_receive:
            log_anomaly(
                metric='network_rx',
                device=interface,
                avg_short=avg_short_receive,
                avg_long=avg_long_receive,
                threshold=adaptive_threshold_receive,
            )

        if avg_short_transmit > adaptive_threshold_transmit:
            log_anomaly(
                metric='network_tx',
                device=interface,
                avg_short=avg_short_transmit,
                avg_long=avg_long_transmit,
                threshold=adaptive_threshold_transmit,
            )


async def run_anomaly_checks() -> None:
    while True:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(check_cpu())
            tg.create_task(check_ram())
            tg.create_task(check_disk())
            tg.create_task(check_net())
        await asyncio.sleep(30)