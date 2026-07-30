from storage import get_known_devices, get_known_interfaces, read_cpu_recent, read_disk_recent, read_net_recent, read_ram_recent

CPU_SHORT_WINDOW, CPU_LONG_WINDOW = 5, 60
RAM_SHORT_WINDOW, RAM_LONG_WINDOW = 5, 60
DISK_SHORT_WINDOW, DISK_LONG_WINDOW = 10, 120
NET_SHORT_WINDOW, NET_LONG_WINDOW = 8, 90


async def check_cpu(threshold: float) -> None:
    long_window = await read_cpu_recent(limit=CPU_LONG_WINDOW)
    if len(long_window) < CPU_LONG_WINDOW:
        return None

    short_window = long_window[:CPU_SHORT_WINDOW]

    avg_cpu_usage_short = sum(metric['usage_percentage'] for metric in short_window) / CPU_SHORT_WINDOW
    avg_cpu_usage_long = sum(metric['usage_percentage'] for metric in long_window) / CPU_LONG_WINDOW

    if avg_cpu_usage_short > avg_cpu_usage_long * threshold:
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

