#!/usr/bin/python3

from purity_fb import PurityFb, rest

import argparse
import os
import smtplib
import ssl
import sys

# Requirements: environments variables FB_MGMT_VIP and FB_MGMT_TOKEN.

# Disable warnings related to unsigned SSL certificates on the FlashBlade.
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def humanize_bytes(num: int) -> str:
    suffix = "B"
    for unit in ["", "K", "M", "G", "T", "P"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def parse_bytes_string(input_string: str) -> int:
    if input_string.endswith("KB"):
        return int(input_string[:-2]) * 1024
    elif input_string.endswith("MB"):
        return int(input_string[:-2]) * 1024 * 1024
    elif input_string.endswith("GB"):
        return int(input_string[:-2]) * 1024 * 1024 * 1024
    elif input_string.endswith("TB"):
        return int(input_string[:-2]) * 1024 * 1024 * 1024 * 1024
    elif input_string.endswith("PB"):
        return int(input_string[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024
    else:
        return int(input_string)


# Create PurityFb object for a certain array using environment variables.
FB_MGMT = os.environ.get('PUREFB_URL')
TOKEN = os.environ.get('PUREFB_API')

SMTP_ADDRESS = os.environ.get('SMTP_EMAIL')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')


if not FB_MGMT or not TOKEN:
    print("Error. Requires FB_MGMT and TOKEN environment variables.")
    sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("--account", default="default")
parser.add_argument("--quota", default="0")
parser.add_argument("--enforce", dest='enforce', action='store_true')

args = parser.parse_args()

account_name = args.account
quota_bytes = parse_bytes_string(args.quota)


# Create management object.
fb = PurityFb(FB_MGMT)
fb.disable_verify_ssl()

try:
    fb.login(TOKEN)
except rest.ApiException as e:
    print("Exception: %s\n" % e)
    sys.exit(1)


info_text = []
total_account_bytes = 0
try:
    for res in fb.buckets.list_buckets(filter='account.name=\'' + account_name + '\'').items:
        total_account_bytes += res.space.virtual
        info_text.append("Bucket " + res.name + " " + humanize_bytes(res.space.virtual))
    info_text.append("Total for " + account_name + " = " + humanize_bytes(total_account_bytes))

except rest.ApiException as e:
    print("Unable to list buckets. Exception: %s\n" % e)
    sys.exit(1)

print("\n".join(info_text))

if total_account_bytes > quota_bytes:
    print("WARN Quota of {} exceeded for account {}".format(args.quota, account_name))

    if SMTP_ADDRESS:
        print("Sending warning email through {}".format(SMTP_ADDRESS))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", context=context) as server:
            server.login(SMTP_ADDRESS, SMTP_PASSWORD)
            receiver_email = "joshua@purestorage.com"
            message = "Subject: WARN Quota of {} exceeded for account {}".format(args.quota, account_name)
            message = message + "\n\n" + "\n".join(info_text)
            server.sendmail(SMTP_ADDRESS, receiver_email, message)

    if args.enforce:
        # Collect list of policies, in case we need to replace 'full-access'
        disabled_policies = ['pure:policy/full-access', 'pure:policy/object-write']
        res = fb.object_store_access_policies.list_object_store_access_policies()
        all_policies = [r.name for r in res.items if r.name not in disabled_policies]

        # List of all users in this account.
        res = fb.object_store_users.list_object_store_users(filter='name=\'' + account_name + '/*\'')
        users = [r.name for r in res.items]

        recovery_commands = []

        # For each user, remove the object-write policy. Handle 'full-access' special case.
        for user in users:
            # Get existing policies for the user.
            res = fb.object_store_access_policies.list_object_store_access_policies_object_store_users(member_names=[user])
            user_policies = [r.policy.name for r in res.items]

            if 'pure:policy/full-access' in user_policies:
                # Replace full-access  with the list of constituent policies.
                add_policies = [p for p in all_policies if p not in user_policies]
                print("Downgrading user {} from full-access policy. Adding: {}".format(user, ",".join(add_policies)))
                for policy in add_policies:
                    res = fb.object_store_access_policies.add_object_store_access_policies_object_store_users(member_names=[user], policy_names=[policy])
                    recovery_commands.append("purepolicy obj access remove --user {} {}".format(user, policy))

                # Then, remove full-access
                res = fb.object_store_access_policies.remove_object_store_access_policies_object_store_users(
                    member_names=[user], policy_names=["pure:policy/full-access"])
                recovery_commands.append("purepolicy obj access add --user {} {}".format(user, "pure:policy/full-access"))

            if 'pure:policy/object-write' in user_policies:
                res = fb.object_store_access_policies.remove_object_store_access_policies_object_store_users(
                    member_names=[user], policy_names=["pure:policy/object-write"])
                recovery_commands.append("purepolicy obj access add --user {} {}".format(user, "pure:policy/object-write"))

        if recovery_commands:
            print("To recover policies back to original state, issue the following CLI commands:")
            for c in recovery_commands:
                print(c)

fb.logout()
