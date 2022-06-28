FROM ubuntu:latest
RUN echo "tzdata tzdata/Areas select Europe" >> /tmp/timezone.cfg; \
    echo "tzdata tzdata/Zones/Europe select London" >> /tmp/timezone.cfg; \
    debconf-set-selections /tmp/timezone.cfg && \
    rm -f /etc/timezone /etc/localtime && \
    apt-get update && \
    apt-get install -y tzdata xtide xtide-data-nonfree
RUN useradd -m -s /bin/bash ubuntu;
USER ubuntu
ENTRYPOINT ["/usr/bin/tide"]
