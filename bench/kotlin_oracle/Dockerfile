# The Kotlin answer key's environment: JDK 21, the Android SDK, the Kotlin compilers the e2e
# repositories build with, and TypeUses built for each of them. linux/amd64: AGP's aapt2 and
# the Kotlin/Native compiler ship for x86_64 Linux hosts only (on an arm64 Mac this runs
# under Rosetta). Gradle itself comes from each checkout's wrapper; Gradle's caches and
# Kotlin/Native's distributions live in Docker volumes.
FROM eclipse-temurin:21-jdk-noble@sha256:02414d70acea327645d412e9794da6e3e2bec41d8c56c283fda875afb5cc2211
RUN apt-get update && apt-get install -y --no-install-recommends unzip git && rm -rf /var/lib/apt/lists/*
ENV ANDROID_HOME=/opt/android-sdk
RUN mkdir -p $ANDROID_HOME/cmdline-tools && cd /tmp \
 && curl -sSLo tools.zip https://dl.google.com/android/repository/commandlinetools-linux-16111833_latest.zip \
 && echo "e025545c62a8e64c7559119566a569fb1dec5f60  tools.zip" | sha1sum -c - \
 && unzip -q tools.zip && mv cmdline-tools $ANDROID_HOME/cmdline-tools/latest && rm tools.zip \
 && yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses >/dev/null \
 && $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platforms;android-37.0" "build-tools;37.0.0" "platform-tools" >/dev/null
# the compilers (Maven Central, pinned by SHA-256): nowinandroid builds with 2.3.0, Ktor
# with 2.3.21, and Gradle 9.7.1's kotlin-dsl (nowinandroid's build-logic) with 2.4.0
COPY compiler.sha256 /opt/kotlin/
RUN cd /opt/kotlin && while read sum path; do curl -sSfO "https://repo1.maven.org/maven2/$path"; done < compiler.sha256 \
 && sed 's|  .*/|  |' compiler.sha256 | sha256sum -c --quiet -
COPY kotlinc /usr/local/bin/kotlinc
# TypeUses, compiled by each compiler against itself: a compiler plugin's FIR API changes
# between versions (/opt/type-uses/type-uses-<version>.jar)
COPY TypeUses /opt/type-uses/src
COPY typeuses.init.gradle /opt/type-uses/
RUN cd /opt/type-uses && for v in 2.3.0 2.3.21 2.4.0; do \
      rm -rf classes && kotlinc $v -no-stdlib -no-reflect -nowarn -jvm-target 1.8 -Xcontext-parameters \
        -opt-in=org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi \
        -cp /opt/kotlin/kotlin-compiler-embeddable-$v.jar:/opt/kotlin/kotlin-stdlib-$v.jar \
        -d classes src/TypeUses.kt \
      && cp -r src/META-INF classes/ && jar cf type-uses-$v.jar -C classes . || exit 1; \
    done && rm -rf classes
