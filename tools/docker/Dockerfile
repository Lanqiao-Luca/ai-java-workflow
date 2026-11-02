ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS tooling
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 unzip ca-certificates && rm -rf /var/lib/apt/lists/*
COPY maven.tar.gz gradle.zip /tmp/ajw-tools/
RUN mkdir -p /opt/maven && tar -xzf /tmp/ajw-tools/maven.tar.gz -C /opt/maven --strip-components=1 && unzip -q /tmp/ajw-tools/gradle.zip -d /opt && mv /opt/gradle-8.14.3 /opt/gradle && rm -rf /tmp/ajw-tools
ENV JAVA_HOME=/opt/java/openjdk MAVEN_HOME=/opt/maven GRADLE_HOME=/opt/gradle
FROM tooling AS public_cache
COPY seed /tmp/warm/app
COPY prewarm.py /opt/ajw/prewarm.py
ENV HOME=/tmp/warm/home TMPDIR=/tmp/warm/tmp GRADLE_USER_HOME=/tmp/warm/home/gradle
RUN ["/usr/bin/python3", "-I", "-B", "/opt/ajw/prewarm.py"]
FROM tooling AS runtime
COPY --from=public_cache /opt/cache-seed /opt/cache-seed
COPY worker.py /opt/ajw/worker.py
RUN mkdir -p /workspace /sandbox/home /sandbox/tmp && chown 1000:1000 /workspace /sandbox/home /sandbox/tmp
ARG CONTEXT_ID
ARG WORKER_SHA256
LABEL io.ai-java-workflow.fixture="spring-build-v1" io.ai-java-workflow.context="${CONTEXT_ID}" io.ai-java-workflow.worker-sha256="${WORKER_SHA256}" io.ai-java-workflow.java="${JAVA_VERSION}"
USER 1000:1000
WORKDIR /workspace
ENTRYPOINT ["/usr/bin/python3", "-I", "-B", "/opt/ajw/worker.py"]
