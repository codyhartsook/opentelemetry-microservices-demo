FROM prom/prometheus:latest
COPY conf.yml .
EXPOSE 9090
CMD [ "--config.file=conf.yml", "--web.enable-remote-write-receiver" ]