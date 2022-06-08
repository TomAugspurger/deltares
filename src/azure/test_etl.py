import etl

from stactools.deltares import stac

URL = "https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/LIDAR/5km/GFM_global_LIDAR5km_2018slr_rp0000.nc"  # noqa: E501


def test_etl_single() -> None:
    item = stac.create_item(URL)
    endpoint = "https://deltaresfloodssa.blob.core.windows.net/references" ""
    item2, refs = etl.do_one_sansio(item, endpoint=endpoint)

    assert (
        item2.assets["references"].href
        == "https://deltaresfloodssa.blob.core.windows.net/references/floods/LIDAR-5km-2018-0000.json"  # noqa: E501
    )
    assert item2.assets["references"].roles == ["index"]
    assert isinstance(refs, dict)
