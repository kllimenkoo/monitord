import asyncio
import statistics

from storage import get_known_devices, get_known_interfaces, read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

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


async def check_ram() -> None:
    long_window = await read_ram_recent(limit=RAM_LONG_WINDOW)
    if len(long_window) < RAM_LONG_WINDOW:
        return None

    short_window = long_window[:RAM_SHORT_WINDOW]

    long_window_values_ram = [metric['mem_usage_percentage'] for metric in long_window]
    short_window_values_ram = [metric['mem_usage_percentage'] for metric in short_window]

    avg_long_window_ram = sum(long_window_values_ram) / len(long_window)
    avg_short_window_ram = sum(short_window_values_ram) / len(short_window)

    long_window_stdev_ram = max(statistics.stdev(long_window_values_ram), RAM_STDEV_FLOOR)
    adaptive_threshold_ram = avg_long_window_ram + (RAM_SENSITIVITY * long_window_stdev_ram)

    long_window_values_swap = [metric['swap_usage_percentage'] for metric in long_window]
    short_window_values_swap = [metric['swap_usage_percentage'] for metric in short_window]

    avg_long_window_swap = sum(long_window_values_swap) / len(long_window)
    avg_short_window_swap = sum(short_window_values_swap) / len(short_window)

    long_window_stdev_swap = max(statistics.stdev(long_window_values_swap), RAM_SENSITIVITY)
    adaptive_threshold_swap = avg_long_window_swap + (RAM_SENSITIVITY * long_window_stdev_swap)

    if avg_short_window_ram > adaptive_threshold_ram:
        print('Something is wrong: RAM is doing heavy lifting.')

    if avg_short_window_swap > adaptive_threshold_swap:
        print('Something is wrong: swap is doing heavy lifting.')


async def check_disk() -> None:
    devices = await get_known_devices()
    for device in devices:
        long_window = await read_disk_recent(device=device, limit=DISK_LONG_WINDOW)
        if len(long_window) < DISK_LONG_WINDOW:
            continue

        short_window = long_window[:DISK_SHORT_WINDOW]

        long_window_values = [row['io_utilization_percentage'] for row in long_window]
        short_window_values = [row['io_utilization_percentage'] for row in short_window]

        avg_long_window = sum(long_window_values) / len(long_window)
        avg_short_window = sum(short_window_values) / len(short_window)

        long_window_stdev = max(statistics.stdev(long_window_values), DISK_STDEV_FLOOR)
        adaptive_threshold = avg_long_window + (DISK_SENSITIVITY * long_window_stdev)

        if avg_short_window > adaptive_threshold:
            print(f'Something is wrong: disk {device} is doing too much work.')


async def check_net() -> None:
    interfaces = await get_known_interfaces()
    for interface in interfaces:
        long_window = await read_net_recent(interface=interface, limit=NET_LONG_WINDOW)
        if len(long_window) < NET_LONG_WINDOW:
            continue

        short_window = long_window[:NET_SHORT_WINDOW]

        long_window_values_receive = [row['receive_bytes_per_sec'] for row in long_window]
        short_window_values_receive = [row['receive_bytes_per_sec'] for row in short_window]

        avg_long_window_receive = sum(long_window_values_receive) / len(long_window)
        avg_short_window_receive = sum(short_window_values_receive) / len(short_window)

        long_window_stdev_receive = max(statistics.stdev(long_window_values_receive), NET_STDEV_FLOOR)
        adaptive_threshold_receive = avg_long_window_receive + (NET_SENSITIVITY * long_window_stdev_receive)

        long_window_values_transmit = [row['transmit_bytes_per_sec'] for row in long_window]
        short_window_values_transmit = [row['transmit_bytes_per_sec'] for row in short_window]

        avg_long_window_transmit = sum(long_window_values_transmit) / len(long_window)
        avg_short_window_transmit = sum(short_window_values_transmit) / len(short_window)

        long_window_stdev_transmit = max(statistics.stdev(long_window_values_transmit), NET_STDEV_FLOOR)
        adaptive_threshold_transmit = avg_long_window_transmit + (NET_SENSITIVITY * long_window_stdev_transmit)

        if avg_short_window_receive > adaptive_threshold_receive:
            print(f'Something is wrong: big amount of data received over the {interface} interface.')

        if avg_short_window_transmit > adaptive_threshold_transmit:
            print(f'Something is wrong: big amount of data sent over the {interface} interface.')


async def run_anomaly_checks() -> None:
    while True:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(check_cpu())
            tg.create_task(check_ram())
            tg.create_task(check_disk())
            tg.create_task(check_net())
