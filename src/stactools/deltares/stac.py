from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
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
    Link,
    MediaType,
    Provider,
    ProviderRole,
    RelType,
    SpatialExtent,
    Summaries,
    TemporalExtent,
)
from pystac.extensions.item_assets import ItemAssetsExtension

logger = logging.getLogger(__name__)

NETCDF_MEDIA_TYPE = "application/x-netcdf"
DATA_ASSET_TITLE = "Flood Map"
DATA_ASSET_DESCRIPTION = (
    "Inundation maps of flood depth using a model that takes into "
    "account water level attenuation and is forced by sea level."
)
DATA_ASSET_ROLES = ["data"]

CUBE_DIMENSIONS = {
    "time": {
        "extent": ["2010-01-01T00:00:00Z", "2010-01-01T00:00:00Z"],
        "description": "time",
        "type": "temporal",
    },
    "lon": {
        "axis": "x",
        "extent": [-179.975, 179.97500000000005],
        "description": "longitude",
        "reference_system": {
            "$schema": "https://proj.org/schemas/v0.4/projjson.schema.json",
            "type": "GeographicCRS",
            "name": "undefined",
            "datum": {
                "type": "GeodeticReferenceFrame",
                "name": "World Geodetic System 1984",
                "ellipsoid": {
                    "name": "WGS 84",
                    "semi_major_axis": 6378137,
                    "inverse_flattening": 298.257223563,
                },
                "id": {"authority": "EPSG", "code": 6326},
            },
            "coordinate_system": {
                "subtype": "ellipsoidal",
                "axis": [
                    {
                        "name": "Longitude",
                        "abbreviation": "lon",
                        "direction": "east",
                        "unit": "degree",
                    },
                    {
                        "name": "Latitude",
                        "abbreviation": "lat",
                        "direction": "north",
                        "unit": "degree",
                    },
                ],
            },
        },
        "type": "spatial",
    },
    "lat": {
        "axis": "y",
        "extent": [-89.97500000000002, 89.975],
        "description": "latitude",
        "reference_system": {
            "$schema": "https://proj.org/schemas/v0.4/projjson.schema.json",
            "type": "GeographicCRS",
            "name": "undefined",
            "datum": {
                "type": "GeodeticReferenceFrame",
                "name": "World Geodetic System 1984",
                "ellipsoid": {
                    "name": "WGS 84",
                    "semi_major_axis": 6378137,
                    "inverse_flattening": 298.257223563,
                },
                "id": {"authority": "EPSG", "code": 6326},
            },
            "coordinate_system": {
                "subtype": "ellipsoidal",
                "axis": [
                    {
                        "name": "Longitude",
                        "abbreviation": "lon",
                        "direction": "east",
                        "unit": "degree",
                    },
                    {
                        "name": "Latitude",
                        "abbreviation": "lat",
                        "direction": "north",
                        "unit": "degree",
                    },
                ],
            },
        },
        "type": "spatial",
    },
}
CUBE_VARIABLES = {
    "projection": {
        "type": "data",
        "description": "wgs84",
        "dimensions": [],
        "attrs": {
            "long_name": "wgs84",
            "EPSG_code": "EPSG:4326",
            "proj4_params": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
            "grid_mapping_name": "latitude_longitude",
        },
        "shape": [],
    },
    "inun": {
        "type": "data",
        "description": "Coastal flooding",
        "dimensions": ["time", "lat", "lon"],
        "unit": "m",
        "attrs": {
            "units": "m",
            "standard_name": "water_surface_height_above_reference_datum",
            "long_name": "Coastal flooding",
        },
        "shape": [1, 3600, 7200],
        "chunks": [1, 3600, 7200],
    },
}


def create_collection(extra_fields: dict[str, Any] | None) -> Collection:
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

    date_intervals: list[datetime | None] = [None, None]

    extent = Extent(
        SpatialExtent([[-180.0, 90.0, 180.0, -90.0]]),
        TemporalExtent([date_intervals]),
    )
    extra_fields = extra_fields or {}
    extra_fields["cube:variables"] = CUBE_VARIABLES
    extra_fields["cube:dimensions"] = CUBE_DIMENSIONS

    collection = Collection(
        id="deltares-floods",
        title="Deltares Global Flood Maps",
        description="Global estimates of coastal inundation under various sea level rise conditions and return periods at 90m, 1km, and 5km resolutions. Also includes estimated coastal inundation caused by named historical storm events going back several decades.",  # noqa: E501
        license="CDLA-Permissive-1.0",
        providers=providers,
        extent=extent,
        catalog_type=CatalogType.RELATIVE_PUBLISHED,
        extra_fields=extra_fields,
        stac_extensions=[
            "https://stac-extensions.github.io/datacube/v2.0.0/schema.json"
        ],
    )

    collection.add_links(
        [
            Link(
                "describedby",
                target="https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/11206409-003-ZWS-0003_v0.1-Planetary-Computer-Deltares-global-flood-docs.pdf",  # noqa: E501
                media_type="application/pdf",
                title="User Guide",
            ),
            Link(
                RelType.LICENSE,
                target="https://cdla.dev/permissive-1-0/",  # noqa: E501
                media_type="text/html",
                title="Community Data License Agreement – Permissive, Version 1.0",
            ),
        ]
    )

    SUMMARIES = {
        "deltares:dem_name": ["NASADEM", "MERITDEM", "LIDAR"],
        "deltares:resolution": ["90m", "1km", "5km"],
        "deltares:sea_level_year": [2018, 2050],
        "deltares:return_period": [
            "0000",
            "0002",
            "0005",
            "0010",
            "0025",
            "0050",
            "0100",
            "0250",
        ],
    }

    collection.summaries = Summaries(SUMMARIES, maxcount=50)
    ItemAssetsExtension.add_to(collection)
    collection.extra_fields["item_assets"] = {
        "data": {
            "type": NETCDF_MEDIA_TYPE,
            "title": DATA_ASSET_TITLE,
            "description": DATA_ASSET_DESCRIPTION,
            "roles": DATA_ASSET_ROLES,
        }
    }

    collection.add_asset(
        "thumbnail",
        Asset(
            "https://ai4edatasetspublicassets.azureedge.net/assets/pc_thumbnails/additional_datasets/deltares-flood.png",  # noqa: E501
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
    # TODO: Might want to download the NetCDF file locally.
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
            title=DATA_ASSET_TITLE,
            description=DATA_ASSET_DESCRIPTION,
            media_type=NETCDF_MEDIA_TYPE,
            roles=DATA_ASSET_ROLES,
        ),
    )
    return item
