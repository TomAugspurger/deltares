from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import fsspec
import shapely.geometry
import xarray as xr
import xstac
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
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


@dataclass
class PathParts:
    dem_name: str
    resolution: str
    sea_level_year: int
    return_period: str

    XPR = re.compile(
        r"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/[^/]+/[^/]+[^/]+/[^/]+/GFM_global_"  # noqa: E501
        r"(?P<dem_name>NASADEM|MERITDEM|LIDAR)"
        r"(?P<resolution>[^_]+)_"
        r"(?P<sea_level_year>\d{4})slr_rp"
        r"(?P<return_period>\d+)"
    )

    @classmethod
    def from_url(cls, url: str) -> "PathParts":
        match = cls.XPR.match(url)
        if not match:
            raise ValueError(f"URL {url} does not match the regular expresion.")
        d: dict[str, Any] = match.groupdict()
        d["sea_level_year"] = int(d["sea_level_year"])
        return cls(**d)

    @property
    def item_id(self) -> str:
        return "-".join(
            [
                self.dem_name,
                self.resolution,
                str(self.sea_level_year),
                self.return_period,
            ]
        )


def create_item(
    asset_href: str, transform_href: Callable[[str], str] | None = None
) -> Item:
    """
    Create a STAC item from a URL to a Kerchunk index file.

    Parameters
    ----------
    asset_href : str
        URL to the NetCDF file.
    """
    if transform_href is None:

        def transform_href(x: str) -> str:
            return x

    assert callable(transform_href)
    parts = PathParts.from_url(asset_href)
    geom = shapely.geometry.box(-180, -90, 180, 90)
    with fsspec.open(asset_href).open() as f:
        ds = xr.open_dataset(f, engine="h5netcdf", chunks={})

        template = Item(
            parts.item_id,
            shapely.geometry.mapping(geom),
            geom.bounds,
            ds.time.to_pandas().dt.to_pydatetime()[0],
            {},
        )
        item: Item = xstac.xarray_to_stac(ds, template)

    for k, v in asdict(parts).items():
        item.properties[f"deltares:{k}"] = v

    item.add_asset(
        "data",
        Asset(
            asset_href,
            title="Index file",
            description="Kerchunk index file with references to the original data.",
            media_type="application/x-netcdf",
            roles=["index"],
        ),
    )
    return item
