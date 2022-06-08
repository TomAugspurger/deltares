examples/collection.json:
	stac deltares create-collection $@


examples/pc-collection.json:
	stac deltares create-collection $@ \
		--extra-field "msft:storage_account=deltaresfloodssa" \
		--extra-field "msft:container=floods" \
		--extra-field "msft:short_description=Global estimates of coastal inundation under various sea level rise conditions and return periods."
