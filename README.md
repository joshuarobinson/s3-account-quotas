# s3-account-quotas

WARNING: this project is not actively maintained as of Apr-2022

Python script to implement a quota enforcement algorithm per Object Store Account

Example invocation:
```
PUREFB_URL=$FB_MGMT_VIP PUREFB_API=$FB_MGMT_TOKEN python3 s3-account-quota.py --account myaccount --quota 10TB
```
