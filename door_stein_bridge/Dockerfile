ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-requests py3-yaml
COPY diagnose.py /diagnose.py
COPY bridge.py /bridge.py
COPY security_selftest.py /security_selftest.py
COPY run /etc/services.d/door-stein/run
RUN chmod 0755 /etc/services.d/door-stein/run
