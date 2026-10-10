FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir numpy==2.5.3 && pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
COPY worker.py /runner.py
ENV OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
WORKDIR /agent
ENTRYPOINT ["python", "-I", "-u", "/runner.py"]
