# The C++ answer key's environment: Clang/LLVM 23.1.6 from the LLVM project's own release
# (pinned by SHA-256; apt.llvm.org keeps only its latest build), Ubuntu 24.04's GCC 13
# libstdc++ as the standard library, CMake and Ninja for compile_commands.json, and the
# development packages POCO's optional components need. Linux on the host's architecture
# (arm64 on an arm64 Mac), and TypeUses built against that Clang (/opt/type-uses/type-uses).
FROM ubuntu:24.04@sha256:562111b88caa79c71391c0c4d3c2114a7d5c35915c20561fd893cb1e07929e6b
ARG LLVM=23.1.6
ARG LLVM_SHA256=be9ce7840a8f5273cb22305cc6227f737f05735d84df889dad0e123660902698
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl zstd xz-utils git g++ make cmake ninja-build pkg-config python3 \
      libssl-dev libmysqlclient-dev libpq-dev unixodbc-dev \
      apache2-dev libapr1-dev libaprutil1-dev \
      libavahi-client-dev libavahi-compat-libdnssd-dev libssh-dev libxml2-dev \
      zlib1g-dev libexpat1-dev libpcre2-dev libsqlite3-dev libudev-dev \
 && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && curl -sSfLo llvm.tar.zst \
      https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVM/LLVM-$LLVM-Linux-ARM64.tar.zst \
 && echo "$LLVM_SHA256  llvm.tar.zst" | sha256sum -c - \
 && mkdir /opt/llvm && tar -I "zstd --long=31" -xf llvm.tar.zst -C /opt/llvm --strip-components=1 \
 && rm llvm.tar.zst \
 && rm -rf /opt/llvm/lib/liblldb* /opt/llvm/lib/libMLIR* /opt/llvm/lib/libmlir* /opt/llvm/lib/libFortran* \
           /opt/llvm/lib/libflang* /opt/llvm/include/mlir /opt/llvm/include/flang /opt/llvm/include/lldb
ENV PATH=/opt/llvm/bin:$PATH
# leveldb's db_bench_tree_db.cc benchmarks Kyoto Cabinet
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libkyotocabinet-dev \
 && rm -rf /var/lib/apt/lists/*
COPY TypeUses /opt/type-uses/src
RUN cmake -S /opt/type-uses/src -B /tmp/tu -G Ninja -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release \
      -DClang_DIR=/opt/llvm/lib/cmake/clang >/dev/null \
 && ninja -C /tmp/tu >/dev/null && cp /tmp/tu/type-uses /opt/type-uses/ && rm -rf /tmp/tu
