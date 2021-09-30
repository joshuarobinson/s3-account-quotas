FROM python:3.9-slim

RUN pip3 install purity-fb

COPY *.py /opt/

ENTRYPOINT ["python", "/opt/s3-account-quota.py"]
