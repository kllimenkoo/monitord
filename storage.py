import time

import aiosqlite

from models import DiskMetrics, NetMetrics, RamMetrics

DB_PATH = '/var/lib/monitord/metrics.db'
_db: aiosqlite.Connection | None = None
tables: tuple = (
    """
    CREATE TABLE IF NOT EXISTS cpu_metrics(
        timestamp REAL,
        usage_percentage REAL
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS ram_metrics(
        timestamp REAL,
        mem_usage_percentage REAL,
        swap_usage_percentage REAL
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS disk_metrics(
        timestamp REAL,
        device TEXT,
        read_iops REAL,
        read_bytes_per_sec REAL,
        write_iops REAL,
        write_bytes_per_sec REAL,
        io_utilization_percentage REAL
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS net_metrics(
        timestamp REAL,
        interface TEXT,
        receive_bytes_per_sec REAL,
        receive_packets_per_sec REAL,
        transmit_bytes_per_sec REAL,
        transmit_packets_per_sec REAL,
        receive_packet_error_count REAL,
        receive_packet_drop_count REAL,
        transmit_packet_error_count REAL,
        transmit_packet_drop_count REAL
    )
    """.strip()
)


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH, autocommit=True)
        await _db.execute('PRAGMA journal_mode=WAL')
        _db.row_factory = aiosqlite.Row

    return _db


async def init_db() -> None:
    db = await get_db()
    for sql in tables:
        await db.execute(sql)


async def write_cpu(usage_percentage: float | None) -> None:
    db = await get_db()
    await db.execute(
        'INSERT INTO cpu_metrics VALUES (?, ?)', (time.time(), usage_percentage)
    )


async def write_ram(metrics: RamMetrics) -> None:
    db = await get_db()
    await db.execute(
        'INSERT INTO ram_metrics VALUES (?, ?, ?)',
        (time.time(), metrics.mem_usage_percentage, metrics.swap_usage_percentage),
    )


async def write_disk(metrics: dict[str, DiskMetrics]) -> None:
    db = await get_db()
    for device, dev_metrics in metrics.items():
        await db.execute(
            'INSERT INTO disk_metrics VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                time.time(),
                device,
                dev_metrics.read_iops,
                dev_metrics.read_bytes_per_sec,
                dev_metrics.write_iops,
                dev_metrics.write_bytes_per_sec,
                dev_metrics.io_utilization_percentage,
            ),
        )


async def write_net(metrics: dict[str, NetMetrics]) -> None:
    db = await get_db()
    for interface, intf_metrics in metrics.items():
        await db.execute(
            'INSERT INTO net_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                time.time(),
                interface,
                intf_metrics.receive_bytes_per_sec,
                intf_metrics.receive_packets_per_sec,
                intf_metrics.transmit_bytes_per_sec,
                intf_metrics.transmit_packets_per_sec,
                intf_metrics.receive_packet_error_count,
                intf_metrics.receive_packet_drop_count,
                intf_metrics.transmit_packet_error_count,
                intf_metrics.transmit_packet_drop_count,
            ),
        )


async def read_cpu_recent(limit: int) -> list[aiosqlite.Row]:
    db = await get_db()
    async with db.execute(
        """
        SELECT timestamp, usage_percentage FROM cpu_metrics
        ORDER BY timestamp DESC LIMIT ?
        """,
        (limit,),
    ) as cursor:
        result = await cursor.fetchall()
    return result  # type: ignore


async def read_ram_recent(limit: int) -> list[aiosqlite.Row]:
    db = await get_db()
    async with db.execute(
        """
        SELECT timestamp, mem_usage_percentage, swap_usage_percentage
        FROM ram_metrics ORDER BY timestamp DESC LIMIT ?
        """,
        (limit,),
    ) as cursor:
        result = await cursor.fetchall()
    return result  # type: ignore


async def read_disk_recent(device: str, limit: int) -> list[aiosqlite.Row]:
    db = await get_db()
    async with db.execute(
        """
        SELECT timestamp, device, read_iops,
        read_bytes_per_sec, write_iops, write_bytes_per_sec,
        io_utilization_percentage
        FROM disk_metrics
        WHERE device = ? ORDER BY timestamp DESC LIMIT ?
        """,
        (device, limit),
    ) as cursor:
        result = await cursor.fetchall()
    return result  # type: ignore


async def read_net_recent(interface: str, limit: int) -> list[aiosqlite.Row]:
    db = await get_db()
    async with db.execute(
        """
        SELECT timestamp, interface,
        receive_bytes_per_sec, receive_packets_per_sec,
        transmit_bytes_per_sec, transmit_packets_per_sec,
        receive_packet_error_count, receive_packet_drop_count,
        transmit_packet_error_count, transmit_packet_drop_count
        FROM net_metrics
        WHERE interface = ? ORDER BY timestamp DESC LIMIT ?
        """,
        (interface, limit),
    ) as cursor:
        result = await cursor.fetchall()
    return result  # type: ignore


async def get_known_devices() -> list[str]:
    db = await get_db()
    async with db.execute('SELECT DISTINCT device FROM disk_metrics') as cursor:
        result = await cursor.fetchall()
    return [device for (device,) in result]


async def get_known_interfaces() -> list[str]:
    db = await get_db()
    async with db.execute('SELECT DISTINCT interface FROM net_metrics') as cursor:
        result = await cursor.fetchall()
    return [interface for (interface,) in result]
