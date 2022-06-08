from pystac import Link, RelType

NETCDF_MEDIA_TYPE = "application/x-netcdf"

LICENSE = Link(
    RelType.LICENSE,
    target="https://cdla.dev/permissive-1-0/",  # noqa: E501
    media_type="text/html",
    title="Community Data License Agreement – Permissive, Version 1.0",
)

DATA_ASSET_TITLE = "Flood Map"
DATA_ASSET_DESCRIPTION = (
    "Inundation maps of flood depth using a model that takes into "
    "account water level attenuation and is forced by sea level."
)
DATA_ASSET_ROLES = ["data"]

FLOOD_CUBE_DIMENSIONS = {
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
FLOOD_CUBE_VARIABLES = {
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
    },
}


AVAILABILITY_CUBE_DIMENSIONS = {
    "time": {
        "extent": [None, "2020-12-31T00:00:00Z"],
        "step": "P1DT0H0M0S",
        "type": "temporal",
    },
    "GrandID": {
        "type": "identifier",
        "extent": [None, None],
        "description": "GrandID number of the reservoir of interest",
    },
    "ksathorfrac": {
        "type": "level",
        "values": [5, 20, 50, 100, 250],
        "description": "Five different value lateral anisotropy values used",
    },
}


AVAILABILITY_CUBE_VARIABLES = {
    "latitude": {
        "type": "data",
        "description": "Latitude of reservoir",
        "dimensions": ["GrandID"],
        "unit": "degrees",
        "attrs": {"units": "degrees", "description": "Latitude of reservoir"},
        "longitude": {
            "type": "data",
            "description": "Longitude of reservoir",
            "dimensions": ["GrandID"],
            "unit": "degrees",
            "attrs": {"units": "degrees", "description": "Longitude of reservoir"},
        },
        "P_res": {
            "type": "data",
            "description": "Precipitation reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {"units": "mm per day", "description": "Precipitation reservoir"},
        },
        "Ea_res": {
            "type": "data",
            "description": "Simulated actual evaporation reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {
                "units": "mm per day",
                "description": "Simulated actual evaporation reservoir",
            },
        },
        "Qout_res": {
            "type": "data",
            "description": "Simulated reservoir outflow",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "m3 per s",
            "attrs": {
                "units": "m3 per s",
                "description": "Simulated reservoir outflow",
            },
        },
        "Qin_res": {
            "type": "data",
            "description": "Simulated reservoir inflow (surface+subsurface)",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "m3 per s",
            "attrs": {
                "units": "m3 per s",
                "description": "Simulated reservoir inflow (surface+subsurface)",
            },
        },
        "S_res": {
            "type": "data",
            "description": "Simulated reservoir volume",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "m3",
            "attrs": {"units": "m3", "description": "Simulated reservoir volume"},
        },
        "FracFull": {
            "type": "data",
            "description": "Simulated reservoir volume",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "m3",
            "attrs": {"units": "m3", "description": "Simulated reservoir volume"},
        },
        "P": {
            "type": "data",
            "description": "Average precipitation upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {
                "units": "mm per day",
                "description": "Average precipitation upstream of reservoir",
            },
        },
        "ETa": {
            "type": "data",
            "description": "Average simulated actual evapotransporation upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {
                "units": "mm per day",
                "description": "Average simulated actual evapotransporation upstream of reservoir",
            },
        },
        "Snow": {
            "type": "data",
            "description": "Average simulated snow depth upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm",
            "attrs": {
                "units": "mm",
                "description": "Average simulated snow depth upstream of reservoir",
            },
        },
        "Melt": {
            "type": "data",
            "description": "Average simulated snow melt upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {
                "units": "mm per day",
                "description": "Average simulated snow melt upstream of reservoir",
            },
        },
        "Temp": {
            "type": "data",
            "description": "Average surface temperature upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "degrees C",
            "attrs": {
                "units": "degrees C",
                "description": "Average surface temperature upstream of reservoir",
            },
        },
        "PET": {
            "type": "data",
            "description": "Average potential evapotranspiration upstream of reservoir",
            "dimensions": ["time", "GrandID", "ksathorfrac"],
            "unit": "mm per day",
            "attrs": {
                "units": "mm per day",
                "description": "Average potential evapotranspiration upstream of reservoir",
            },
        },
    },
}
