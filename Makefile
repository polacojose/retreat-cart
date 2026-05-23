build:
	podman build -t python-woolworths-api .
	podman run --rm python-woolworths-api
