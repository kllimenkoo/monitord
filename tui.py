import asyncio

import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Label, ProgressBar

API_BASE = 'http://localhost:8000'


def first(response: httpx.Response, key: str, default: float = 0.0) -> float:
    try:
        data = response.json()
        return data[0].get(key, default) if data else default
    except Exception:
        return default


class MetricApp(App):
    CSS = """
    Screen {
        background: #0a0a12;
        text-style: italic;
        color: #b700ff;
    }

    Header {
        background: #520380;
        color: #C8A2C8;
    }

    Footer {
        background: #520380;
        color: #C8A2C8;
    }
 
    PercentageStatus {
        color: #C89FE0;
    }

    Bar > .bar--bar {
        color: #7A29A8;
        background: #C89FE0;
    }

    Bar > .bar--complete {
        color: $error;
    }

    .container {
        margin: 1;
        padding: 1 1;
        border: heavy #520380;
        background: #0f0f1e;
    }

    .container > Label {
        color: #C8A2C8;
    }

    .sub-label {
        color: #b700ff;
        text-style: italic;
        margin-top: 1;
    }
    """

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

    async def on_mount(self) -> None:
        async with httpx.AsyncClient() as client:
            devices_response = await client.get(f'{API_BASE}/get_device_names')
            devices = devices_response.json()

            disk_container = self.query_one('#disk-container', Vertical)
            for device in devices:
                await disk_container.mount(
                    Label(f'{device.upper()}', classes='sub-label')
                )
                await disk_container.mount(
                    ProgressBar(total=100, id=f'disk-{device}-bar', show_eta=False)
                )

            interfaces_response = await client.get(f'{API_BASE}/get_interface_names')
            interfaces = interfaces_response.json()

            net_container = self.query_one('#net-container', Vertical)
            for interface in interfaces:
                await net_container.mount(Label(f'{interface}', classes='sub-label'))
                await net_container.mount(
                    Label(
                        '↓ 0.0 B/s ↑ 0.0 B/s',
                        id=f'net-{interface}-label',
                        classes='sub-label',
                    )
                )

            self.poll_metrics(devices, interfaces)

    def format_bytes(self, bps: float) -> str:
        if bps >= 1000000:
            return f'{bps / 1000000:.1f} Mb/s'
        elif bps >= 1000:
            return f'{bps / 1000:.1f} Kb/s'
        else:
            return f'{bps:.0f} B/s'

    @work(exclusive=True)
    async def poll_metrics(self, devices: list[str], interfaces: list[str]) -> None:
        """Poll FastAPI every 2 seconds and update bars."""
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    cpu_response = await client.get(f'{API_BASE}/cpu?limit=1')
                    ram_response = await client.get(f'{API_BASE}/ram?limit=1')

                    cpu_bar = self.query_one('#cpu-bar', ProgressBar)
                    cpu_bar.progress = first(
                        cpu_response, 'usage_percentage'
                    )

                    mem_bar = self.query_one('#ram-bar', ProgressBar)
                    mem_bar.progress = first(
                        ram_response, 'mem_usage_percentage'
                    )

                    swap_bar = self.query_one('#swap-bar', ProgressBar)
                    swap_bar.progress = first(
                        ram_response, 'swap_usage_percentage'
                    )

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
                            f'↓ {self.format_bytes(receive)}   '
                            f'↑ {self.format_bytes(transmit)}'
                        )
                except httpx.RequestError:
                    pass

                await asyncio.sleep(2)


if __name__ == '__main__':
    MetricApp().run()
