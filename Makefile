build:
	podman build -t python-woolworths-api .
	podman run --rm -p 8000:8000 python-woolworths-api
