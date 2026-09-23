import asyncio

import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, ProgressBar, RichLog

API_BASE = 'http://localhost:8000'


def first(response: httpx.Response, key: str, default: float = 0.0) -> float:
    try:
        data = response.json()
        return data[0].get(key, default) if data else default
    except Exception:
        return default


class AlertScreen(ModalScreen):
    """Pop up window with alerts."""

    BINDINGS = [('a', 'dismiss', 'Close'), ('escape', 'dismiss', 'Close')]

    def compose(self) -> ComposeResult:
        with Vertical(id='alerts-container'):
            yield Label('Anomaly Alerts', id='alerts-title')
            yield RichLog(auto_scroll=False)

    async def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.scroll_home(animate=False)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{API_BASE}/alerts')
                alerts = response.json()['alerts']
                if not alerts:
                    log.write('No alerts yet.')
                    return
                for line in reversed(alerts):
                    log.write(line)
        except httpx.RequestError:
            log.write('Cannot reach daemon.')


class MonitordApp(App):
    TITLE = 'monitord'
    CSS_PATH = 'app.tcss'
    BINDINGS = [('a', 'request_alerts', 'alerts'), ('q', 'quit', 'quit')]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id='cpu-container', classes='container'):
                yield Label('CPU Usage')
                yield ProgressBar(total=100, id='cpu-bar', show_eta=False)

            with Vertical(id='ram-container', classes='container'):
                yield Label('Ram Usage')
                yield ProgressBar(total=100, id='ram-bar', show_eta=False)

                yield Label('Swap Usage')
                yield ProgressBar(total=100, id='swap-bar', show_eta=False)

        with Horizontal():
            with Vertical(id='disk-container', classes='container'):
                yield Label('Disk IO Utilization')

            with Vertical(id='net-container', classes='container'):
                yield Label('Network Throughput')
        yield Footer()

    def action_request_alerts(self) -> None:
        self.push_screen(AlertScreen())

    async def discover(self, client: httpx.AsyncClient) -> tuple[list[str], list[str]]:
        """Fetch device and interface names and populate containers."""
        devices_response = await client.get(f'{API_BASE}/get_device_names')
        devices = devices_response.json()

        disk_container = self.query_one('#disk-container', Vertical)
        await disk_container.query('Label.sub-label').remove()
        await disk_container.query('ProgressBar').remove()
        for device in devices:
            await disk_container.mount(Label(f'{device.upper()}', classes='sub-label'))
            await disk_container.mount(
                ProgressBar(total=100, id=f'disk-{device}-bar', show_eta=False)
            )

        interfaces_response = await client.get(f'{API_BASE}/get_interface_names')
        interfaces = interfaces_response.json()

        net_container = self.query_one('#net-container', Vertical)
        await net_container.query('Label.sub-label').remove()
        await net_container.query('ProgressBar').remove()
        for interface in interfaces:
            await net_container.mount(Label(f'{interface}', classes='sub-label'))
            await net_container.mount(
                Label(
                    '↓ 0.0 KB/s ↑ 0.0 KB/s',
                    id=f'net-{interface}-label',
                    classes='sub-label',
                )
            )
        return devices, interfaces

    async def on_mount(self) -> None:
        self.poll_metrics()

    @work(exclusive=True)
    async def poll_metrics(self) -> None:
        """Poll FastAPI every 2 seconds and update bars."""
        devices: list[str] = []
        interfaces: list[str] = []
        was_unreachable: bool = True
        error_notified: bool = False

        async with httpx.AsyncClient() as client:
            while True:
                try:
                    if was_unreachable:
                        devices, interfaces = await self.discover(client=client)
                        if error_notified:
                            self.notify('Daemon reconnected', severity='information')
                        was_unreachable = False

                    error_notified = False

                    cpu_response = await client.get(f'{API_BASE}/cpu?limit=1')
                    ram_response = await client.get(f'{API_BASE}/ram?limit=1')

                    cpu_bar = self.query_one('#cpu-bar', ProgressBar)
                    cpu_bar.progress = first(cpu_response, 'usage_percentage')

                    mem_bar = self.query_one('#ram-bar', ProgressBar)
                    mem_bar.progress = first(ram_response, 'mem_usage_percentage')

                    swap_bar = self.query_one('#swap-bar', ProgressBar)
                    swap_bar.progress = first(ram_response, 'swap_usage_percentage')

                    for device in devices:
                        disk_response = await client.get(
                            f'{API_BASE}/disk/{device}?limit=1'
                        )
                        disk_percentage = first(
                            disk_response, 'io_utilization_percentage'
                        )

                        disk_bar = self.query_one(f'#disk-{device}-bar', ProgressBar)
                        disk_bar.progress = disk_percentage

                    for interface in interfaces:
                        net_response = await client.get(
                            f'{API_BASE}/net/{interface}?limit=1'
                        )
                        receive = first(net_response, 'receive_bytes_per_sec')
                        transmit = first(net_response, 'transmit_bytes_per_sec')

                        interface_label = self.query_one(
                            f'#net-{interface}-label', Label
                        )
                        interface_label.update(
                            f'↓ {receive / 1000:.1f} KB/s  ↑ {transmit / 1000:.1f} KB/s'
                        )

                except httpx.RequestError:
                    was_unreachable = True
                    if not error_notified:
                        self.notify('Cannot reach daemon', severity='error', timeout=10)
                        error_notified = True

                await asyncio.sleep(2)


if __name__ == '__main__':
    MonitordApp().run()
