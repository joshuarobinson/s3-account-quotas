#!/bin/bash

set -e

IMGNAME=joshuarobinson/s3-account-quota

FB_MGMT_VIP=REPLACE
FB_MGMT_TOKEN=T-REPLACE

ACCOUNT="default"
QUOTA="1TB"

docker run -it --rm \
  -e PUREFB_URL=$FB_MGMT_VIP -e PUREFB_API=$FB_MGMT_TOKEN \
  -e SMTP_EMAIL="something@gmail.com" -e SMTP_PASSWORD="secret" \
  $IMGNAME --account $ACCOUNT --quota $REPLACE
