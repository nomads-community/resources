from collections import OrderedDict

import click

from resources.install.commands import install
from resources.update.commands import update


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
    Standardisation, extraction and visualisation of NOMADS experimental and sequencing data

    """
    pass


# ================================================================
# Individual sub-commands
# ================================================================

cli.add_command(install)
cli.add_command(update)


if __name__ == "__main__":
    cli()
