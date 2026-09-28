FROM ubuntu@sha256:496754492fb28b4d3049432f2ca787449331e23fb14f0dd3fffea86bf5a93eb4
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates build-essential bc bison flex libssl-dev libelf-dev \
    python3 perl git xz-utils zlib1g-dev clang-18 llvm-18 lld-18 \
    && dpkg-query -W > /build-packages.txt && rm -rf /var/lib/apt/lists/*
ENV PATH="/usr/lib/llvm-18/bin:${PATH}"
