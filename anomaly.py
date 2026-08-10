import asyncio
import statistics

from storage import get_known_devices, get_known_interfaces, read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

CPU_SHORT_WINDOW, CPU_LONG_WINDOW = 5, 20
CPU_SENSITIVITY = 2.0
CPU_STDEV_FLOOR = 0.5

RAM_SHORT_WINDOW, RAM_LONG_WINDOW = 5, 20
DISK_SHORT_WINDOW, DISK_LONG_WINDOW = 10, 20
NET_SHORT_WINDOW, NET_LONG_WINDOW = 8, 20

RAM_THRESHOLD = 1.5
DISK_THRESHOLD = 2.0
NET_THRESHOLD = (2.0, 2.0)


async def check_cpu() -> None:
    long_window = await read_cpu_recent(limit=CPU_LONG_WINDOW)
    if len(long_window) < CPU_LONG_WINDOW:
        return None

    short_window = long_window[:CPU_SHORT_WINDOW]

    long_window_values = [metric['usage_percentage'] for metric in long_window]
    short_window_values = [metric['usage_percentage'] for metric in short_window]

    avg_long_window = sum(long_window_values) / len(long_window)
    avg_short_window = sum(short_window_values) / len(short_window)

    long_window_stdev = max(statistics.stdev(long_window_values), CPU_STDEV_FLOOR)
    adaptive_threshold = avg_long_window + (CPU_SENSITIVITY * long_window_stdev)

    if avg_short_window > adaptive_threshold:
        print('Something is wrong: CPU is doing heavy lifting.')

async def check_ram(threshold: float) -> None:
    long_window = await read_ram_recent(limit=RAM_LONG_WINDOW)
    if len(long_window) < RAM_LONG_WINDOW:
        return None

    short_window = long_window[:RAM_SHORT_WINDOW]

    avg_mem_usage_short = sum(metric['mem_usage_percentage'] for metric in short_window) / RAM_SHORT_WINDOW
    avg_mem_usage_long = sum(metric['mem_usage_percentage'] for metric in long_window) / RAM_LONG_WINDOW

    avg_swap_usage_short = sum(metric['swap_usage_percentage'] for metric in short_window) / RAM_SHORT_WINDOW
    avg_swap_usage_long = sum(metric['swap_usage_percentage'] for metric in long_window) / RAM_LONG_WINDOW

    if avg_mem_usage_short > avg_mem_usage_long * threshold:
        print('Something is wrong: RAM is doing heavy lifting.')

    if avg_swap_usage_short > avg_swap_usage_long * threshold:
        print('Something is wrong: swap is doing heavy lifting.')


async def check_disk(threshold: float) -> None:
    devices = await get_known_devices()
    for device in devices:
        long_window = await read_disk_recent(device=device, limit=DISK_LONG_WINDOW)
        if len(long_window) < DISK_LONG_WINDOW:
            continue

        short_window = long_window[:DISK_SHORT_WINDOW]

        avg_io_utilization_short = sum(row['io_utilization_percentage'] for row in short_window) / DISK_SHORT_WINDOW
        avg_io_utilization_long = sum(row['io_utilization_percentage'] for row in long_window) / DISK_LONG_WINDOW

        if avg_io_utilization_short > avg_io_utilization_long * threshold:
            print(f'Something is wrong: disk {device} is doing too much work.')


async def check_net(threshold: tuple[float, float]) -> None:
    interfaces = await get_known_interfaces()
    for interface in interfaces:
        long_window = await read_net_recent(interface=interface, limit=NET_LONG_WINDOW)
        if len(long_window) < NET_LONG_WINDOW:
            continue

        short_window = long_window[:NET_SHORT_WINDOW]

        avg_receive_short = sum(row['receive_bytes_per_sec'] for row in short_window) / NET_SHORT_WINDOW
        avg_transmit_short = sum(row['transmit_bytes_per_sec'] for row in short_window) / NET_SHORT_WINDOW

        avg_receive_long = sum(row['receive_bytes_per_sec'] for row in long_window) / NET_LONG_WINDOW
        avg_transmit_long = sum(row['transmit_bytes_per_sec'] for row in long_window) / NET_LONG_WINDOW

        if avg_receive_short > avg_receive_long * threshold[0]:
            print(f'Something is wrong: big amount of data received over the {interface} interface.')

        if avg_transmit_short > avg_transmit_long * threshold[1]:
            print(f'Something is wrong: big amount of data sent over the {interface} interface.')


async def run_anomaly_checks() -> None:
    while True:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(check_cpu())
            tg.create_task(check_ram(RAM_THRESHOLD))
            tg.create_task(check_disk(DISK_THRESHOLD))
            tg.create_task(check_net(NET_THRESHOLD))
        await asyncio.sleep(30)
