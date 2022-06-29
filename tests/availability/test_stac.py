import planetary_computer

from stactools.deltares.availability import stac


def test_availability() -> None:
    # ugh, 390 MiB...
    asset_href = "https://deltaresreservoirssa.blob.core.windows.net/reservoirs/v2021.12/reservoirs_BOM.nc"  # noqa: E501
    result = stac.create_item(asset_href, transform_href=planetary_computer.sign)
    assert result.id == "BOM"
    assert result.bbox
    result.validate()
