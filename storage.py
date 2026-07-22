import time
import aiosqlite

from models import RamMetrics, DiskMetrics, NetMetrics


DB_PATH = "/var/lib/monitord/metrics.db"
_db: aiosqlite.Connection | None = None
tables: tuple = (
    """
    CREATE TABLE IF NOT EXISTS cpu_metrics(
        timestamp REAL,
        usage_percentage REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ram_metrics(
        timestamp REAL,
        mem_total INTEGER,
        mem_free INTEGER,
        swap_total INTEGER,
        swap_free INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS disk_metrics(
        timestamp REAL,
        dev_name TEXT,
        read_iops REAL,
        read_bytes_per_sec REAL,
        write_iops REAL,
        write_bytes_per_sec REAL,
        io_utilization_percent REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS net_metrics(
        timestamp REAL,
        intf_name TEXT,
        receive_bytes_per_sec REAL,
        receive_packets_per_sec REAL,
        transmit_bytes_per_sec REAL,
        transmit_packets_per_sec REAL,
        receive_packet_error_count REAL,
        receive_packet_drop_count REAL,
        transmit_packet_error_count REAL,
        transmit_packet_drop_count REAL
    )
    """
)


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH, autocommit=True)
        await _db.execute("PRAGMA journal_mode=WAL")

    return _db


async def init_db() -> None:
    db = await get_db()
    for sql in tables:
        await db.execute(sql)


async def write_cpu(usage_percentage: float) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO cpu_metrics VALUES (?, ?)",
        (time.time(), usage_percentage)
    )


async def write_ram(metrics: RamMetrics) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO ram_metrics VALUES (?, ?, ?, ?, ?)",
        (time.time(), metrics.mem_total, metrics.mem_available, metrics.swap_total,
         metrics.swap_free)
    )


async def write_disk(metrics: dict[str, DiskMetrics]) -> None:
    db = await get_db()
    for dev_name, dev_metrics in metrics.items():
        await db.execute(
            "INSERT INTO disk_metrics VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), dev_name, dev_metrics.read_iops, dev_metrics.read_bytes_per_sec,
            dev_metrics.write_iops, dev_metrics.write_bytes_per_sec, dev_metrics.io_utilization_percent)
        )


async def write_net(metrics: dict[str, NetMetrics]) -> None:
    db = await get_db()
    for intf_name, intf_metrics in metrics.items():
        await db.execute(
            "INSERT INTO net_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), intf_name, intf_metrics.receive_bytes_per_sec, intf_metrics.receive_packets_per_sec,
            intf_metrics.transmit_bytes_per_sec, intf_metrics.transmit_packets_per_sec,
            intf_metrics.receive_packet_error_count, intf_metrics.receive_packet_drop_count,
            intf_metrics.transmit_packet_error_count, intf_metrics.transmit_packet_drop_count)
        )
