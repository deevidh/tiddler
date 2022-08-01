FROM ubuntu:latest
COPY --chmod=755 generate-tidal-data.sh /usr/bin/
RUN echo tzdata tzdata/Areas select Europe | debconf-set-selections; \
    echo tzdata tzdata/Zones/Europe select London | debconf-set-selections; \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata xtide xtide-data-nonfree awscli;
RUN useradd -m -s /bin/bash ubuntu;
USER ubuntu
CMD ["/usr/bin/generate-tidal-data.sh"]
