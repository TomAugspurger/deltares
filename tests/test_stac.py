from stactools.deltares import stac


def test_create_item() -> None:
    asset_href = "https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/LIDAR/5km/GFM_global_LIDAR5km_2018slr_rp0000.nc"  # noqa: E501

    result = stac.create_item(asset_href)
    assert result.id == "LIDAR-5km-2018-0000"
    assert result.properties["deltares:dem_name"] == "LIDAR"
    assert result.properties["deltares:resolution"] == "5km"
    assert result.properties["deltares:sea_level_year"] == 2018
    assert result.properties["deltares:return_period"] == 0
