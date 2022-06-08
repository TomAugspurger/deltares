from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import urllib.request
from typing import Any

import dask.distributed
import dask_gateway
import pystac

import azure.storage.blob

logger = logging.getLogger(__name__)


xpr = re.compile(
    r"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/[^/]+/[^/]+[^/]+/[^/]+/GFM_global_"  # noqa: E501
    r"(?P<dem_name>NASADEM|MERITDEM|LIDAR)"
    r"(?P<resolution>[^_]+)_"
    r"(?P<sea_level_year>\d{4})slr_rp"
    r"(?P<return_period>\d+)"
)


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
    return f"floods/{item.id}.json"


def get_stac_blob_name(item: pystac.Item) -> str:
    return f"floods/{item.id}.json"


def do_one_sansio(
    item: pystac.Item,
    endpoint: str,
    filename: str | None = None,
) -> tuple[pystac.Item, dict[str, Any]]:
    refs = make_refs(item, filename=filename)
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
) -> None:
    from stactools.deltares import stac

    refs_cc = azure.storage.blob.ContainerClient(**references_container_client_options)
    stac_cc = azure.storage.blob.ContainerClient(**stac_container_client_options)

    with tempfile.NamedTemporaryFile() as tf:
        filename = tf.name

        item = stac.create_item(asset_href, filename=filename)

        refs_name = get_references_blob_name(item)
        stac_name = get_stac_blob_name(item)

        with refs_cc.get_blob_client(refs_name) as bc:
            if not bc.exists():
                item, refs = do_one_sansio(
                    item, refs_cc.primary_endpoint, filename=filename
                )
                bc.upload_blob(
                    json.dumps(refs).encode(),
                    overwrite=True,
                    content_settings=azure.storage.blob.ContentSettings(
                        content_type=str(pystac.MediaType.JSON)
                    ),
                )

        assert bc.exists()

    with stac_cc.get_blob_client(stac_name) as bc:
        bc.upload_blob(
            json.dumps(item.to_dict()).encode(),
            overwrite=True,
            content_settings=azure.storage.blob.ContentSettings(
                content_type=str(pystac.MediaType.GEOJSON)
            ),
        )


def main() -> None:
    cc = azure.storage.blob.ContainerClient(
        "https://deltaresfloodssa.blob.core.windows.net", "floods"
    )
    account_url = "https://deltaresfloodssa.blob.core.windows.net"
    references_container_client_options = dict(
        account_url=account_url,
        container_name="references",
        credential=os.environ["ETL_REFERENCES_CREDENTIAL"],
    )
    stac_container_client_options = dict(
        account_url=account_url,
        container_name="floods-stac",
        credential=os.environ["ETL_STAC_CREDENTIAL"],
    )

    blobs = cc.list_blobs(name_starts_with="v2021.06/global/")
    urls = [f"{cc.primary_endpoint}/{b.name}" for b in blobs if b.name.endswith(".nc")]

    cluster = dask_gateway.GatewayCluster()
    client = cluster.get_client()
    print(client.dashboard_link)
    plugin = dask.distributed.PipInstall(
        ["kerchunk", "git+https://github.com/TomAugspurger/deltares"]
    )
    client.register_worker_plugin(plugin)
    client.upload_file("/code/etl.py")

    cluster.adapt(minimum=8, maximum=40)
    futures_to_urls = {
        client.submit(
            do_one,
            url,
            references_container_client_options=references_container_client_options,
            stac_container_client_options=stac_container_client_options,
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
            logger.exception("Error in %s", url)
            failure.append(url)
        else:
            success.append(url)
    print("\n".join(failure))


if __name__ == "__main__":
    main()
