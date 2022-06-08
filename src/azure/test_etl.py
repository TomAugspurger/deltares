import etl

URL = "https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/NASADEM/90m/GFM_global_NASADEM90m_2018slr_rp0100_masked.nc"  # noqa: E501


def test_match() -> None:
    result = etl.DeltaresRecord.from_url(URL)
    assert result.item_id == "NASADEM-90m-2018-0100"


def test_netcdf_name() -> None:
    result = etl.DeltaresRecord.from_url(URL)
    assert (
        result.netcdf_name
        == "v2021.06/global/NASADEM/90m/GFM_global_NASADEM90m_2018slr_rp0100_masked.nc"
    )


def test_references_name() -> None:
    result = etl.DeltaresRecord.from_url(URL)
    assert result.references_name == "floods/NASADEM-90m-2018-0100.json"
