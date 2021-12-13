FROM python:3.10-slim

RUN pip3 install purity-fb
RUN pip3 show purity-fb

COPY *.py /opt/

ENTRYPOINT ["python", "/opt/s3-account-quota.py"]
