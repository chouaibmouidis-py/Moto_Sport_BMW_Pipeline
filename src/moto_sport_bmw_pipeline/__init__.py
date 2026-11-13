"""IMSA data engineering services; importing the package never starts a pipeline."""


def main() -> None:
    """Expose the source checkout's pipeline launcher as the uv console command."""
    from .orchestration import main as run

    run(None)
