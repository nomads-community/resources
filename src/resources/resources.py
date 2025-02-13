from collections import OrderedDict
from pathlib import Path

import click

from resources.install.commands import install
from resources.lib.logging import config_root_logger
from resources.update.commands import update

# Configure logging before subcommand execution
resources_dir = Path(__file__).parent.parent.parent.resolve()
log_dir = resources_dir / "logs"
config_root_logger(log_dir=log_dir, verbose=False)


class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or OrderedDict()

    def list_commands(self, ctx):
        return self.commands


@click.group(cls=OrderedGroup)
@click.version_option(message="%(prog)s-v%(version)s")
def cli():
    """
    Install and maintain NOMADS software tools

    """
    pass


# ================================================================
# Individual sub-commands
# ================================================================

cli.add_command(install)
cli.add_command(update)


if __name__ == "__main__":
    cli()
