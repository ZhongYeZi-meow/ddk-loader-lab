FROM python@sha256:b68d40df862ac07e8955ea0fc0c5454cb4245b6165e79bc8ea2cc69170d9ba62 AS python2
FROM ubuntu@sha256:496754492fb28b4d3049432f2ca787449331e23fb14f0dd3fffea86bf5a93eb4
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates build-essential bc bison flex libssl-dev libelf-dev \
    python3 python-is-python3 perl git xz-utils zlib1g-dev clang-18 llvm-18 lld-18 \
    gcc-12-aarch64-linux-gnu \
    && dpkg-query -W > /build-packages.txt && rm -rf /var/lib/apt/lists/*
COPY --from=python2 /usr/local /opt/python2
ENV PATH="/usr/lib/llvm-18/bin:/opt/python2/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/python2/lib"
