from __future__ import annotations

import logging
import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import shapely.geometry
import xarray as xr
import xstac
from pystac import (
    Asset,
    CatalogType,
    Collection,
    Extent,
    Item,
    Link,
    MediaType,
    Provider,
    ProviderRole,
    SpatialExtent,
    Summaries,
    TemporalExtent,
)
from pystac.extensions.item_assets import ItemAssetsExtension

from stactools.deltares import constants

logger = logging.getLogger(__name__)


NUMBER_OF_BASINS = {
    "ERA5": 3236,
    "CHIRPS": 2951,
    "EOBS": 682,
    "NLDAS": 1090,
    "BOM": 116,
}


def create_collection(
    description: str | None = None, extra_fields: dict[str, Any] | None = None
) -> Collection:
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
            name="Deltares",
            roles=[ProviderRole.PRODUCER],
            url="https://www.deltares.nl/en/",
        ),
        Provider(
            name="Microsoft",
            roles=[ProviderRole.HOST],
            url="https://planetarycomputer.microsoft.com/",
        ),
    ]

    date_intervals: list[datetime | None] = [
        datetime(1970, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 12, 31, tzinfo=timezone.utc),
    ]

    extent = Extent(
        SpatialExtent([[-180.0, 90.0, 180.0, -90.0]]),
        TemporalExtent([date_intervals]),
    )
    extra_fields = extra_fields or {}
    extra_fields["cube:variables"] = constants.AVAILABILITY_CUBE_VARIABLES
    extra_fields["cube:dimensions"] = constants.AVAILABILITY_CUBE_DIMENSIONS

    if description is None:
        description = "Daily reservoir variations for 3,236 locations across the globe for the period 1970-2020."  # noqa: E501

    collection = Collection(
        id="deltares-water-availability",
        title="Deltares Global Water Availability",
        description=description,
        license="CDLA-Permissive-1.0",
        providers=providers,
        extent=extent,
        catalog_type=CatalogType.RELATIVE_PUBLISHED,
        extra_fields=extra_fields,
        stac_extensions=[
            "https://stac-extensions.github.io/datacube/v2.0.0/schema.json"
        ],
    )
    collection.keywords = [
        "Deltares",
        "Water availability",
        "Reservoir",
        "Water",
        "Precipitation",
    ]

    links = [
        Link(
            "documentation",
            "https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/pc-deltares-water-availability-documentation.pdf",  # noqa: E501
            media_type="application/pdf",
            title="User Guide",
        ),
        constants.LICENSE,
    ]
    collection.add_links(links)

    SUMMARIES = {
        "deltares:reservoir": ["ERA5", "CHIRPS", "EOBS", "NLDAS", "BOM"],
    }

    collection.summaries = Summaries(SUMMARIES, maxcount=50)
    ItemAssetsExtension.add_to(collection)
    collection.extra_fields["item_assets"] = {
        "data": {
            "type": constants.NETCDF_MEDIA_TYPE,
            "title": constants.DATA_ASSET_TITLE,
            "description": constants.DATA_ASSET_DESCRIPTION,
            "roles": constants.DATA_ASSET_ROLES,
        },
        "index": {
            "type": MediaType.JSON,
            "title": constants.INDEX_ASSET_TITLE,
            "description": constants.INDEX_ASSET_DESCRIPTION,
            "roles": constants.INDEX_ASSET_ROLES,
        },
    }

    collection.add_asset(
        "thumbnail",
        Asset(
            "https://ai4edatasetspublicassets.azureedge.net/assets/pc_thumbnails/additional_datasets/deltares-reservoir.jpg",  # noqa: E501
            title="Thumbnail",
            media_type=MediaType.PNG,
            roles=["thumbnail"],
        ),
    )

    if extra_fields:
        collection.extra_fields.update(extra_fields)

    return collection


@dataclass
class PathParts:
    reservoir: str

    XPR = re.compile(
        r"https://deltaresreservoirssa.blob.core.windows.net/reservoirs/v2021.12/"
        r"reservoirs_(?P<reservoir>\w+).nc"
    )

    @classmethod
    def from_url(cls, url: str) -> "PathParts":
        match = cls.XPR.match(url)
        if not match:
            raise ValueError(f"URL {url} does not match the regular expression.")
        d = match.groupdict()
        return cls(**d)

    @property
    def item_id(self) -> str:
        return self.reservoir


def create_item_from_dataset(
    ds: xr.Dataset,
    asset_href: str,
) -> Item:
    """"""
    parts = PathParts.from_url(asset_href)

    template = Item(
        parts.item_id,
        None,
        None,
        ds.time.to_pandas().dt.to_pydatetime()[0],
        {},
    )
    longitude = ds.longitude
    latitude = ds.latitude

    bbox = [
        float(x)
        for x in [
            longitude.min().item(),
            latitude.min().item(),
            longitude.max().item(),
            latitude.max().item(),
        ]
    ]
    geometry = shapely.geometry.mapping(shapely.geometry.box(*bbox))

    item: Item = xstac.xarray_to_stac(
        ds, template, temporal_dimension="time", x_dimension=False, y_dimension=False
    )
    item.bbox = bbox
    item.geometry = geometry
    additional_dimensions = {
        "GrandID": {
            "type": "identifier",
            "extent": [int(ds.GrandID.min()), int(ds.GrandID.max())],
            "description": "GrandID number of the reservoir of interest",
        },
        "ksathorfrac": {
            "type": "level",
            "values": ds.ksathorfrac.data.tolist(),
            "description": "Five different value lateral anisotropy values used",
        },
    }
    item.properties["cube:dimensions"].update(additional_dimensions)

    for k, v in asdict(parts).items():
        item.properties[f"deltares:{k}"] = v

    item.add_asset(
        "data",
        Asset(
            asset_href,
            title=constants.DATA_ASSET_TITLE,
            description=constants.DATA_ASSET_DESCRIPTION,
            media_type=constants.NETCDF_MEDIA_TYPE,
            roles=constants.DATA_ASSET_ROLES,
        ),
    )
    return item


def create_item(
    asset_href: str,
    transform_href: Callable[[str], str] | None = None,
    filename: str | None = None,
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

    filename, _ = urllib.request.urlretrieve(
        transform_href(asset_href), filename=filename
    )

    ds = xr.open_dataset(filename, engine="h5netcdf")
    return create_item_from_dataset(ds, asset_href)
