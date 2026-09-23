"""monitord command-line interface.

Commands:
    monitord start    start the systemd service
    monitord stop     stop the systemd service
    monitord status   show the systemd service status
    monitord alerts   show the most recent anomaly alerts
    monitord ui       launch the Textual terminal interface
"""

import os
import shutil
import subprocess
from collections import deque
from pathlib import Path

import typer

app = typer.Typer(
    help='monitord - lightweight Linux system health monitor.',
    no_args_is_help=True,
    add_completion=False,
)

SERVICE = 'monitord'
ALERT_LOG = Path(os.environ.get('MONITORD_ALERT_LOG', '/var/log/monitord/alerts.log'))


def _fail(message: str, code: int = 1) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _systemctl(*args: str, privileged: bool = False) -> int:
    """Run systemctl and return its exit code.

    Privileged actions (start/stop) are prefixed with sudo when the CLI is
    not already running as root.
    """
    if shutil.which('systemctl') is None:
        _fail('systemctl not found - monitord requires a systemd-based system.')

    cmd = ['systemctl', *args]
    if privileged and os.geteuid() != 0:
        if shutil.which('sudo') is None:
            _fail('Root privileges are required and sudo is not available.')
        cmd.insert(0, 'sudo')

    return subprocess.run(cmd).returncode


@app.command()
def start() -> None:
    """Start the monitord service."""
    code = _systemctl('start', f'{SERVICE}.service', privileged=True)
    if code == 0:
        typer.secho('monitord started.', fg=typer.colors.GREEN)
    else:
        typer.secho(
            f'Failed to start monitord. See: journalctl -u {SERVICE} -e',
            fg=typer.colors.RED,
            err=True,
        )
    raise typer.Exit(code)


@app.command()
def stop() -> None:
    """Stop the monitord service."""
    code = _systemctl('stop', f'{SERVICE}.service', privileged=True)
    if code == 0:
        typer.secho('monitord stopped.', fg=typer.colors.GREEN)
    else:
        typer.secho('Failed to stop monitord.', fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


@app.command()
def status() -> None:
    """Show the monitord service status."""
    raise typer.Exit(_systemctl('status', f'{SERVICE}.service', '--no-pager'))


@app.command()
def alerts(
    lines: int = typer.Option(
        20, '--lines', '-n', min=1, help='Number of alerts to show.'
    ),
) -> None:
    """Show the most recent anomaly alerts from the alert log."""
    if not ALERT_LOG.exists():
        typer.echo('No alerts recorded yet.')
        raise typer.Exit()

    tail: deque[str] = deque()
    try:
        with ALERT_LOG.open(encoding='utf-8', errors='replace') as f:
            tail = deque(f, maxlen=lines)
    except PermissionError:
        _fail(f'Permission denied reading {ALERT_LOG}.')

    if not tail:
        typer.echo('No alerts recorded yet.')
        raise typer.Exit()

    for line in tail:
        typer.echo(line.rstrip())


@app.command()
def ui() -> None:
    """Launch the terminal interface (requires the daemon to be running)."""
    from monitord.tui.app import MonitordApp

    MonitordApp().run()


@app.command()
def web() -> None:
    """Open the web dashboard (requires the daemon to be running)."""

    url = 'http://localhost:8000'

    if shutil.which('powershell.exe'):
        subprocess.run(['powershell.exe', '-c', f"Start-Process '{url}'"])
    else:
        import webbrowser

        webbrowser.open(url)


if __name__ == '__main__':
    app()
