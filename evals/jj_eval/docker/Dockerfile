FROM python:3.12-slim
ARG JJ_VERSION=@JJ_VERSION@
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL "https://github.com/jj-vcs/jj/releases/download/v${JJ_VERSION}/jj-v${JJ_VERSION}-$(uname -m)-unknown-linux-musl.tar.gz" \
    | tar -xz -C /usr/local/libexec ./jj
COPY jj-shim /usr/local/bin/jj
COPY jj-eval-editor /usr/local/bin/jj-eval-editor
COPY jj-config.toml /etc/jj-eval/config.toml
RUN git config --system user.name "Eval User" \
 && git config --system user.email eval@example.com \
 && git config --system init.defaultBranch main \
 && git config --system advice.detachedHead false
ENV JJ_CONFIG=/etc/jj-eval/config.toml \
    EDITOR=/usr/local/bin/jj-eval-editor \
    VISUAL=/usr/local/bin/jj-eval-editor \
    GIT_EDITOR=/usr/local/bin/jj-eval-editor
# Build the starting repo, then delete the scenario code so the agent cannot read the checks.
COPY jj_eval /tmp/setup/jj_eval
RUN cd /tmp/setup && python3 -m jj_eval setup @SCENARIO@ && rm -rf /tmp/setup
WORKDIR /app/repo
