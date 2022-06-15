from __future__ import annotations

import json
import logging
import os
import tempfile
import urllib.request
from typing import Any

import dask.distributed
import dask_gateway
import planetary_computer.sas
import pystac
import xarray as xr

import azure.storage.blob

logger = logging.getLogger(__name__)


def make_refs(item: pystac.Item, filename: str | None = None) -> dict[str, Any]:
    import kerchunk.hdf

    asset = item.assets["data"]

    if filename is None:
        filename, _ = urllib.request.urlretrieve(asset.href)

    with open(filename, "rb") as f:
        z = kerchunk.hdf.SingleHdf5ToZarr(f, asset.href)
        refs: dict[str, Any] = z.translate()

    # os.remove(tmpfile)
    return refs


def get_references_blob_name(item: pystac.Item) -> str:
    if "deltaresfloodssa" in item.assets["data"].href:
        return f"floods/{item.id}.json"
    else:
        return f"reservoirs/{item.id}.json"


def do_one_sansio(
    item: pystac.Item,
    endpoint: str,
    filename: str | None = None,
    should_make_refs: bool = True,
) -> tuple[pystac.Item, dict[str, Any] | None]:
    if should_make_refs:
        refs = make_refs(item, filename=filename)
    else:
        refs = None
    refs_name = get_references_blob_name(item)
    item = item.clone()
    item.add_asset(
        "references",
        pystac.Asset(
            f"{endpoint}/{refs_name}",
            title="Index file",
            description="Kerchunk index file.",
            media_type=pystac.MediaType.JSON,
            roles=["index"],
        ),
    )
    return item, refs


def do_one(
    asset_href: str,
    references_container_client_options: dict[str, Any],
    stac_container_client_options: dict[str, Any],
    kind: str,
    # create_item: Callable[..., pystac.Item],
    overwrite_references: bool = False,
    overwrite_item: bool = True,
) -> None:
    if kind == "floods":
        from stactools.deltares import stac
    else:
        from stactools.deltares.availability import stac  # type: ignore

    refs_cc = azure.storage.blob.ContainerClient(**references_container_client_options)
    stac_cc = azure.storage.blob.ContainerClient(**stac_container_client_options)

    with tempfile.NamedTemporaryFile() as tf:
        filename = tf.name
        urllib.request.urlretrieve(asset_href, filename=filename)
        ds = xr.open_dataset(filename, engine="h5netcdf")
        item = stac.create_item_from_dataset(ds, asset_href=asset_href)

        refs_name = stac_name = get_references_blob_name(item)

        with refs_cc.get_blob_client(refs_name) as bc:
            should_make_refs = overwrite_references or not bc.exists()
            item, refs = do_one_sansio(
                item,
                refs_cc.primary_endpoint,
                filename=filename,
                should_make_refs=should_make_refs,
            )
            if should_make_refs:
                assert refs is not None
            if should_make_refs:
                bc.upload_blob(
                    json.dumps(refs).encode(),
                    overwrite=True,
                    content_settings=azure.storage.blob.ContentSettings(
                        content_type=str(pystac.MediaType.JSON)
                    ),
                )

        assert bc.exists()

    with stac_cc.get_blob_client(stac_name) as bc:
        if overwrite_item or not bc.exists():
            bc.upload_blob(
                json.dumps(item.to_dict()).encode(),
                overwrite=True,
                content_settings=azure.storage.blob.ContentSettings(
                    content_type=str(pystac.MediaType.GEOJSON)
                ),
            )


def main(kind: str) -> None:
    assert kind in {"floods", "availability"}

    if kind == "floods":
        cc = azure.storage.blob.ContainerClient(
            "https://deltaresfloodssa.blob.core.windows.net", "floods"
        )
        name_starts_with = "v2021.06/global/"
        account_url = "https://deltaresfloodssa.blob.core.windows.net"
        references_container_client_options = dict(
            account_url=account_url,
            container_name="references",
            credential=os.environ["ETL_FLOODS_REFERENCES_CREDENTIAL"],
        )
        stac_container_client_options = dict(
            account_url=account_url,
            container_name="floods-stac",
            credential=os.environ["ETL_FLOODS_STAC_CREDENTIAL"],
        )

    else:
        account_url = "https://deltaresreservoirssa.blob.core.windows.net"
        cc = azure.storage.blob.ContainerClient(
            account_url,
            "reservoirs",
            credential=planetary_computer.sas.get_token(
                "deltaresreservoirssa", "reservoirs"
            ).token,
        )
        name_starts_with = "v2021.12/"
        references_container_client_options = dict(
            account_url=account_url,
            container_name="references",
            credential=os.environ["ETL_RESERVOIRS_REFERENCES_CREDENTIAL"],
        )
        stac_container_client_options = dict(
            account_url=account_url,
            container_name="reservoirs-stac",
            credential=os.environ["ETL_RESERVOIRS_STAC_CREDENTIAL"],
        )

    blobs = list(cc.list_blobs(name_starts_with=name_starts_with))
    urls = [
        f"{cc.primary_endpoint.split('?')[0]}/{b.name}"
        for b in blobs
        if b.name.endswith(".nc")
    ]
    print(f"{len(urls)=}")

    cluster = dask_gateway.GatewayCluster()
    client = cluster.get_client()
    print(client.dashboard_link)
    plugin = dask.distributed.PipInstall(
        ["kerchunk", "git+https://github.com/TomAugspurger/deltares"]
    )
    client.register_worker_plugin(plugin)
    client.upload_file("/code/etl.py")

    cluster.adapt(minimum=2, maximum=40)

    futures_to_urls = {
        client.submit(
            do_one,
            url,
            references_container_client_options=references_container_client_options,
            stac_container_client_options=stac_container_client_options,
            kind=kind,
            transform_href=planetary_computer.sign,
        ): url
        for url in urls
    }
    dask.distributed.fire_and_forget(list(futures_to_urls))

    success = []
    failure = []

    for future in dask.distributed.as_completed(futures_to_urls):
        url = futures_to_urls[future]
        try:
            future.result()
        except Exception:
            logger.exception("Error in %s", url)
            failure.append(url)
        else:
            success.append(url)
    print("\n".join(failure))


if __name__ == "__main__":
    import sys

    kind = sys.argv[1]
    main(kind)
