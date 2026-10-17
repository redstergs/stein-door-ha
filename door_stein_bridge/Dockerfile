ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-requests py3-yaml
COPY bridge.py /bridge.py
COPY diagnose.py /diagnose.py
CMD ["python3", "-u", "/diagnose.py"]
