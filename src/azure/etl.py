from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import urllib.request
from typing import Any

import dask.distributed
import dask_gateway

import azure.storage.blob

logger = logging.getLogger(__name__)


xpr = re.compile(
    r"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/[^/]+/[^/]+[^/]+/[^/]+/GFM_global_"  # noqa: E501
    r"(?P<dem_name>NASADEM|MERITDEM|LIDAR)"
    r"(?P<resolution>[^_]+)_"
    r"(?P<sea_level_year>\d{4})slr_rp"
    r"(?P<return_period>\d+)"
)


@dataclasses.dataclass
class DeltaresRecord:
    item_id: str
    are_references_created: bool = False
    dataset_id: str = "deltares-floods"

    def __post_init__(self) -> None:
        dem_name, resolution, sea_level_year, return_period = self.item_id.split("-")
        self.dem_name = dem_name
        self.resolution = resolution
        self.sea_level_year = sea_level_year
        self.return_period = return_period

    @classmethod
    def from_url(cls, url: str) -> "DeltaresRecord":
        match = xpr.match(url)
        if not match:
            raise ValueError(f"Bad url {url}")
        d = match.groupdict()
        return cls(
            item_id="-".join(
                [
                    d["dem_name"],
                    d["resolution"],
                    d["sea_level_year"],
                    d["return_period"],
                ]
            )
        )

    @property
    def entity(self) -> dict[str, Any]:
        return {
            "PartitionKey": self.dataset_id,
            "RowKey": self.item_id,
            "are_references_created": self.are_references_created,
        }

    @property
    def netcdf_name(self) -> str:
        return (
            f"v2021.06/global/{self.dem_name}/{self.resolution}/GFM_global_"
            f"{self.dem_name}{self.resolution}_{self.sea_level_year}slr_rp"
            f"{self.return_period}_masked.nc"
        )

    @property
    def references_name(self) -> str:
        return f"floods/{self.item_id}.json"


plugin = dask.distributed.PipInstall(["kerchunk"])


def make_refs(url: str) -> dict[str, Any]:
    import kerchunk

    tmpfile, _ = urllib.request.urlretrieve(url)

    with open(tmpfile, "rb") as f:
        z = kerchunk.hdf.SingleHdf5ToZarr(f, url)
        refs: dict[str, Any] = z.translate()

    os.remove(tmpfile)
    return refs


def put_refs(
    url: str, refs: dict[str, Any], container_client_options: dict[str, Any]
) -> str:
    record: DeltaresRecord = DeltaresRecord.from_url(url)
    refs_cc = azure.storage.blob.ContainerClient(**container_client_options)
    name = record.references_name
    refs_cc.upload_blob(
        name,
        json.dumps(refs).encode(),
        content_settings=azure.storage.blob.ContentSettings(
            content_type="application/json"
        ),
        overwrite=True,
    )
    return name


def do_one(url: str, container_client_options: dict[str, Any]) -> None:
    record = DeltaresRecord.from_url(url)
    refs_cc = azure.storage.blob.ContainerClient(**container_client_options)
    name = record.references_name
    with refs_cc.get_blob_client(name) as bc:
        if not bc.exists():
            refs = make_refs(url)
            put_refs(url, refs, container_client_options=container_client_options)


def main() -> None:
    cc = azure.storage.blob.ContainerClient(
        "https://deltaresfloodssa.blob.core.windows.net", "floods"
    )
    blobs = cc.list_blobs(name_starts_with="v2021.06/global/")
    urls = [f"{cc.primary_endpoint}/{b.name}" for b in blobs]
    container_client_options = dict(
        account_name="deltaresfloodssa",
        credential=os.environ["ETL_REFERENCES_CREDENTIAL"],
    )

    cluster = dask_gateway.GatewayCluster()
    client = cluster.get_client()
    client.register_worker_plugin(plugin)
    cluster.adapt(minimum=1, maximum=40)
    print(client.dashboard_link)
    futures_to_urls = {
        client.submit(
            do_one, url, container_client_options=container_client_options
        ): url
        for url in urls
    }

    success = []
    failure = []

    for future in dask.distributed.as_completed(futures_to_urls):
        url = futures_to_urls[future]
        try:
            future.result()
        except Exception:
            print("error in ", url)
            failure.append(url)
        else:
            success.append(url)
    print("\n".join(failure))


if __name__ == "__main__":
    main()
