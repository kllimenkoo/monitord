from models import RamMetrics, DiskRawData, NetRawData


def read_cpu_stats() -> tuple[int, ...]:
    with open("/proc/stat", "r") as f:
        cpu_line = f.readline()

    fields = cpu_line.strip().split()[1:]
    return tuple(int(i) for i in fields)


def read_ram_stats() -> RamMetrics:
    with open("/proc/meminfo", "r") as f:
        ram_stats = {}
        for line in f:
            key, value = line.strip().split(":")
            ram_stats[key] = int(value.split()[0])

        return RamMetrics(
            mem_total=ram_stats["MemTotal"],
            mem_available=ram_stats["MemAvailable"],
            swap_total=ram_stats["SwapTotal"],
            swap_free=ram_stats["SwapFree"],
        )


def read_disk_stats() -> dict[str, DiskRawData]:
    with open("/proc/diskstats", "r") as f:
        disk_stats = {}
        for line in f:
            fields = line.strip().split()
            device_name = fields[2]
            if device_name.startswith(("sd", "vd", "nvme", "hd")):
                key = device_name
                value = DiskRawData(
                    reads_completed=int(fields[3]),
                    sectors_read=int(fields[5]),
                    writes_completed=int(fields[7]),
                    sectors_written=int(fields[9]),
                    io_time_spent=int(fields[12]),
                )
                disk_stats[key] = value

        return disk_stats


def read_net_stats() -> dict[str, NetRawData]:
    with open("/proc/net/dev", "r") as f:
        net_stats = {}
        for line in f:
            fields = line.strip().split()
            intf_name = fields[0].strip(":")
            if intf_name.startswith(("eth", "ens", "enp", "wlan")):
                key= intf_name
                value = NetRawData(
                    receive_bytes=int(fields[1]),
                    receive_packets=int(fields[2]),
                    receive_errors=int(fields[3]),
                    receive_drops=int(fields[4]),
                    transmit_bytes=int(fields[9]),
                    transmit_packets=int(fields[10]),
                    transmit_errors=int(fields[11]),
                    transmit_drops=int(fields[12]),
                )
                net_stats[key] = value

        return net_stats
