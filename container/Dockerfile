# Tools image for step 11 (real cells from cellweaver) and the worst delay of section 7.
# It is the student pack's dd2-layout-tools image (Yosys 0.33, Magic, Netgen, patched ngspice 47)
# plus OpenSTA built from source (overview Table 1) and cellweaver's pinned Python packages.
# Build it with the cellweaver clone as the context, so its requirements.lock is copied:
#   docker build -t dd2-layout-tools-sta -f container/Dockerfile $HOME/cellweaver
FROM dd2-layout-tools

ARG OPENSTA_COMMIT=f8e13cbf12d02a07a2d1ec4a64f3e6985b747eab

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      cmake swig libfl-dev libeigen3-dev zlib1g-dev python3-venv python3-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# CUDD, which OpenSTA needs
RUN curl -sL https://github.com/ivmai/cudd/archive/refs/tags/cudd-3.0.0.tar.gz | tar xz -C /tmp \
    && cd /tmp/cudd-cudd-3.0.0 && ./configure --prefix=/usr/local && make -j"$(nproc)" && make install \
    && rm -rf /tmp/cudd-cudd-3.0.0

# OpenSTA at a fixed commit; its unit tests are off (they need GTest)
RUN git init -q /tmp/OpenSTA && cd /tmp/OpenSTA \
    && git fetch -q --depth 1 https://github.com/The-OpenROAD-Project/OpenSTA.git ${OPENSTA_COMMIT} \
    && git checkout -q FETCH_HEAD && echo ${OPENSTA_COMMIT} > /opt/opensta_commit.txt \
    && mkdir build && cd build && cmake .. -DCUDD_DIR=/usr/local -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF \
    && make -j"$(nproc)" && make install && rm -rf /tmp/OpenSTA

# cellweaver's Python packages (gdsfactory, klayout), in /opt/cw
COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/cw && /opt/cw/bin/pip install --no-cache-dir -q -r /tmp/requirements.lock

# Netgen at the commit cellweaver was qualified with (1.5.323, docs/technology.md), for step 11 only:
# the image's Netgen reads any file whose name contains ".ext" as a Magic .ext file, so it cannot read
# cellweaver's <cell>.extracted.spice. Installed under /opt/netgen-cw; the image's own netgen is unchanged.
ARG NETGEN_CW_COMMIT=e1528a797cdb155d6ebf8d91c5a55ed7d1713156
RUN git init -q /tmp/netgen && cd /tmp/netgen \
    && git fetch -q --depth 1 https://github.com/RTimothyEdwards/netgen.git ${NETGEN_CW_COMMIT} \
    && git checkout -q FETCH_HEAD && ./configure --prefix=/opt/netgen-cw && make -j"$(nproc)" && make install \
    && rm -rf /tmp/netgen

# Magic at the commit cellweaver was qualified with (8.3.684, 4f53bb3), for step 11 only: cellweaver reads
# the banner "Magic 8.3 revision N", and the image's Magic build prints "Magic 8.3.684 revision 684".
ARG MAGIC_CW_COMMIT=4f53bb3091d1e4a9b2009a58f157a8a4331d4c84
RUN git init -q /tmp/magic && cd /tmp/magic \
    && git fetch -q --depth 1 https://github.com/RTimothyEdwards/magic.git ${MAGIC_CW_COMMIT} \
    && git checkout -q FETCH_HEAD && ./configure --prefix=/opt/magic-cw && make -j"$(nproc)" && make install \
    && rm -rf /tmp/magic

# One OpenMP thread per ngspice run. cellweaver runs --char-jobs ngspice processes at once; with the
# default (one thread per core) 6 jobs start 48 threads on 8 cores and each transient takes ~30x longer,
# past cellweaver's per-context time limit. One thread gives byte-identical waveforms, faster.
RUN sed -i 's/^set num_threads=.*/set num_threads=1/' /usr/local/share/ngspice/scripts/spinit
