from __future__ import annotations

import json
import logging
import pathlib

import click
import pystac
from click import Command, Group

from stactools.deltares import stac

logger = logging.getLogger(__name__)


def create_deltares_command(cli: Group) -> Command:
    """Creates the stactools-deltares command line utility."""

    @cli.group(
        "deltares",
        short_help=("Commands for working with stactools-deltares"),
    )
    def deltares() -> None:
        pass

    @deltares.command(
        "create-collection",
        short_help="Creates a STAC collection",
    )
    @click.argument("destination")
    @click.option(
        "--extra-field",
        default=None,
        help="Key-value pairs to include in extra-fields",
        multiple=True,
    )
    def create_collection_command(destination: str, extra_field: str | None) -> None:
        """Creates a STAC Collection

        Args:
            destination (str): An HREF for the Collection JSON
        """
        extra_fields_d = dict(k.split("=") for k in extra_field)  # type: ignore

        collection = stac.create_collection(extra_fields=extra_fields_d)
        collection.set_self_href(destination)
        collection.validate()
        collection.remove_links(pystac.RelType.SELF)
        collection.remove_links(pystac.RelType.ROOT)

        pathlib.Path(destination).write_text(json.dumps(collection.to_dict(), indent=2))

    @deltares.command("create-item", short_help="Create a STAC item")
    @click.argument("source")
    @click.argument("destination")
    def create_item_command(source: str, destination: str) -> None:
        """Creates a STAC Item

        Args:
            source (str): HREF of the Asset associated with the Item
            destination (str): An HREF for the STAC Collection
        """
        item = stac.create_item(source)

        item.save_object(dest_href=destination)

        return None

    return deltares
