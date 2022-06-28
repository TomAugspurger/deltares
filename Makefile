examples/collection.json:
	stac deltares create-collection $@


examples/pc-floods-collection.json:
	stac deltares create-collection $@ \
		--description "{{ collection.description }}" \
		--extra-field "msft:storage_account=deltaresfloodssa" \
		--extra-field "msft:container=floods" \
		--extra-field "msft:short_description=Global estimates of coastal inundation under various sea level rise conditions and return periods."


examples/item.json:
	stac deltares create-item \
		"https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/LIDAR/5km/GFM_global_LIDAR5km_2018slr_rp0000.nc" \
		examples/item.json

examples/availability-collection.json:
	stac deltares-availability create-collection $@


examples/pc-availability-collection.json:
	stac deltares-availability create-collection $@ \
		--description "{{ collection.description }}" \
		--extra-field "msft:storage_account=deltaresreservoirssa" \
		--extra-field "msft:container=reservoirs" \
		--extra-field "msft:short_description=Historical daily reservoir variations."

