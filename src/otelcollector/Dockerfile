FROM otel/opentelemetry-collector-contrib:latest
COPY conf.yml .
EXPOSE 1888
EXPOSE 13133
EXPOSE 4317
EXPOSE 55670
CMD [ "--config=conf.yml" ]