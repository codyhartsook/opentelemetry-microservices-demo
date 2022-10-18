FROM python:3.8-slim

WORKDIR /src

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 9877

ENTRYPOINT ["python3.8","exporter.py"]