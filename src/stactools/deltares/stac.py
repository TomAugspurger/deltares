from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Callable

import requests
import shapely.geometry
import xarray as xr
import xstac
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
    MediaType,
    Provider,
    ProviderRole,
    SpatialExtent,
    TemporalExtent,
)

logger = logging.getLogger(__name__)


def create_collection() -> Collection:
    """Create a STAC Collection

    This function includes logic to extract all relevant metadata from
    an asset describing the STAC collection and/or metadata coded into an
    accompanying constants.py file.

    See `Collection<https://pystac.readthedocs.io/en/latest/api.html#collection>`_.

    Returns:
        Collection: STAC Collection object
    """
    providers = [
        Provider(
            name="The OS Community",
            roles=[ProviderRole.PRODUCER, ProviderRole.PROCESSOR, ProviderRole.HOST],
            url="https://github.com/stac-utils/stactools",
        )
    ]

    # Time must be in UTC
    demo_time = datetime.now(tz=timezone.utc)

    extent = Extent(
        SpatialExtent([[-180.0, 90.0, 180.0, -90.0]]),
        TemporalExtent([[demo_time, None]]),
    )

    collection = Collection(
        id="my-collection-id",
        title="A dummy STAC Collection",
        description="Used for demonstration purposes",
        license="CC-0",
        providers=providers,
        extent=extent,
        catalog_type=CatalogType.RELATIVE_PUBLISHED,
    )

    return collection


xpr = re.compile(
    r"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/[^/]+/[^/]+[^/]+/[^/]+/GFM_global_"  # noqa: E501
    r"(?P<dem_name>NASADEM|MERITDEM|LIDAR)"
    r"(?P<resolution>[^_]+)_"
    r"(?P<sea_level_year>\d{4})slr_rp"
    r"(?P<return_period>\d+)"
)


def create_item(
    asset_href: str, transform_href: Callable[[str], str] | None = None
) -> Item:
    """
    Create a STAC item from a URL to a Kerchunk index file.

    Parameters
    ----------
    asset_href : str
        https://deltaresfloodssa.blob.core.windows.net/references/floods/GFM_global_MERITDEM90m_2050slr_rp0100_masked.json
    """
    if transform_href is None:

        def transform_href(x: str) -> str:
            return x

    assert callable(transform_href)
    fo = requests.get(transform_href(asset_href)).json()

    # TODO: might need to sign in general

    ds = xr.open_dataset(
        "reference://",
        engine="zarr",
        chunks={},
        storage_options={"fo": fo},
        consolidated=False,
    )

    geom = shapely.geometry.box(-180, -90, 180, 90)
    item_id = asset_href.split("/")[-1].split(".")[0].replace("_", "-")
    template = Item(
        item_id,
        shapely.geometry.mapping(geom),
        geom.bounds,
        ds.time.to_pandas().dt.to_pydatetime()[0],
        {},
    )
    item: Item = xstac.xarray_to_stac(ds, template)

    m = xpr.match(asset_href)
    if m is None:
        raise ValueError(f"Bad url {asset_href}")
    d = m.groupdict()

    item.extra_fields["deltares:dem_name"] = d["dem_name"]
    item.extra_fields["deltares:resolution"] = d["resolutoin"]
    item.extra_fields["deltares:sea_level_year"] = d["sea_level_year"]
    item.extra_fields["deltares:return_period"] = d["return_period"]

    item.add_asset(
        "index",
        Asset(
            asset_href,
            title="Index file",
            description="Kerchunk index file with references to the original data.",
            media_type=MediaType.JSON,
            roles=["index"],
        ),
    )
    assert len(fo["templates"]) == 1
    item.add_asset(
        "data",
        Asset(
            list(fo["templates"].values())[0],
            title="Floods data",
            description="Original data",
            media_type="application/netcdf",
            roles=["data"],
        ),
    )

    return item
