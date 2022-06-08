examples/collection.json:
	stac deltares create-collection $@


examples/pc-collection.json:
	stac deltares create-collection $@ \
		--extra-field "msft:storage_account=deltaresfloodssa" \
		--extra-field "msft:container=floods" \
		--extra-field "msft:short_description=Global estimates of coastal inundation under various sea level rise conditions and return periods."


examples/item.json:
	stac deltares create-item \
		"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/LIDAR/5km/GFM_global_LIDAR5km_2018slr_rp0000.nc" \
		examples/item.json