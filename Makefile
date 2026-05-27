build:
	uv export --no-dev --no-hashes -o requirements.txt
	podman build -t python-woolworths-api .
	podman run --rm -p 8000:8000 python-woolworths-api
