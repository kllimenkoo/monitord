from models import RamRawData, RamMetrics, DiskRawData, DiskMetrics, NetRawData, NetMetrics


def compute_cpu_metrics(prev: tuple[int, ...],
                        curr: tuple[int, ...]) -> float:
    prev_idle = prev[3] + prev[4] # idle + iowait
    curr_idle = curr[3] + curr[4]

    prev_total = sum(prev)
    curr_total = sum(curr)

    delta_idle = curr_idle - prev_idle
    delta_total = curr_total - prev_total

    if delta_total == 0:
        return 0.0

    cpu_usage_percent = 100 * (1 - (delta_idle / delta_total))
    return cpu_usage_percent


def compute_ram_metrics(snapshot: RamRawData) -> RamMetrics:
    mem_usage_percentage = 100 * (1 - (snapshot.mem_available / snapshot.mem_total))

    if snapshot.swap_total > 0:
        swap_usage_percentage = 100 * (1 - (snapshot.swap_free / snapshot.swap_total))
    else:
        swap_usage_percentage = 0.0

    return RamMetrics(
        mem_usage_percentage=mem_usage_percentage,
        swap_usage_percentage=swap_usage_percentage,
    )


def compute_disk_metrics(prev: dict[str, DiskRawData],
                         curr: dict[str, DiskRawData],
                         interval: float) -> dict[str, DiskMetrics]:
    result = {}
    for name, curr_stats in curr.items():
        if name not in prev:
            continue

        if interval == 0:
            continue

        prev_stats = prev[name]

        delta_reads_completed = curr_stats.reads_completed - prev_stats.reads_completed
        delta_sectors_read = curr_stats.sectors_read - prev_stats.sectors_read
        delta_writes_completed = curr_stats.writes_completed - prev_stats.writes_completed
        delta_sectors_written = curr_stats.sectors_written - prev_stats.sectors_written
        delta_io_time = curr_stats.io_time_spent - prev_stats.io_time_spent

        read_iops = delta_reads_completed / interval
        read_bytes_per_sec = (delta_sectors_read * 512) / interval # sector = 512 bytes
        write_iops = delta_writes_completed / interval
        write_bytes_per_sec = (delta_sectors_written * 512) / interval
        io_utilization_percent = 100 * (delta_io_time / (interval * 1000)) # interval to ms

        result[name] = DiskMetrics(
            read_iops=read_iops,
            read_bytes_per_sec=read_bytes_per_sec,
            write_iops=write_iops,
            write_bytes_per_sec=write_bytes_per_sec,
            io_utilization_percent=io_utilization_percent,
        )

    return result


def compute_net_metrics(prev: dict[str, NetRawData],
                        curr: dict[str, NetRawData],
                        interval: float) -> dict[str, NetMetrics]:
    result = {}
    for name, curr_stats in curr.items():
        if name not in prev:
            continue

        prev_stats = prev[name]

        delta_receive_bytes = curr_stats.receive_bytes - prev_stats.receive_bytes
        delta_receive_packets = curr_stats.receive_packets - prev_stats.receive_packets
        delta_transmit_bytes = curr_stats.transmit_bytes - prev_stats.transmit_bytes
        delta_transmit_packets = curr_stats.transmit_packets - prev_stats.transmit_packets 

        receive_bytes_per_sec = delta_receive_bytes / interval
        receive_packets_per_sec = delta_receive_packets / interval
        transmit_bytes_per_sec = delta_transmit_bytes / interval
        transmit_packets_per_sec = delta_transmit_packets / interval

        receive_packet_error_count = curr_stats.receive_errors - prev_stats.receive_errors
        receive_packet_drop_count = curr_stats.receive_drops - prev_stats.receive_drops
        transmit_packet_error_count = curr_stats.transmit_errors - prev_stats.transmit_errors
        transmit_packet_drop_count = curr_stats.transmit_drops - prev_stats.transmit_drops

        result[name] = NetMetrics(
            receive_bytes_per_sec=receive_bytes_per_sec,
            receive_packets_per_sec=receive_packets_per_sec,
            transmit_bytes_per_sec=transmit_bytes_per_sec,
            transmit_packets_per_sec=transmit_packets_per_sec,
            receive_packet_error_count=receive_packet_error_count,
            receive_packet_drop_count=receive_packet_drop_count,
            transmit_packet_error_count=transmit_packet_error_count,
            transmit_packet_drop_count=transmit_packet_drop_count,
        )

    return result
