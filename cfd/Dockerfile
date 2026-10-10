FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openfoam python3-gmsh python3-numpy && rm -rf /var/lib/apt/lists/*
ENV WM_PROJECT_DIR=/usr/share/openfoam
WORKDIR /case
ENTRYPOINT ["/bin/bash", "-c"]
