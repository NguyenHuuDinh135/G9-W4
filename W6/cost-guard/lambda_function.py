"""Automated Cost Guard Lambda for W6 Task 3.

The guard scans EC2 instances and RDS DB instances in the current AWS
region. A resource is allowed to keep running when it has either:

- keep=true
- Environment=dev

Running resources missing both protections are stopped.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Optional safety switch for first deployment/demo rehearsal. Set DRY_RUN=false
# in Terraform for the real W6 acceptance demo so CloudTrail records Stop* calls.
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

KEEP_TAG_KEY = os.getenv("KEEP_TAG_KEY", "keep")
KEEP_TAG_VALUE = os.getenv("KEEP_TAG_VALUE", "true")
ENV_TAG_KEY = os.getenv("ENV_TAG_KEY", "Environment")
ENV_TAG_VALUE = os.getenv("ENV_TAG_VALUE", "dev")

EC2_RUNNING_STATES = {"pending", "running"}
RDS_RUNNING_STATES = {"available"}


def _normalise_tags(tags: list[dict[str, Any]] | None) -> dict[str, str]:
    """Convert AWS tag list shapes into a plain string dict."""
    result: dict[str, str] = {}
    for tag in tags or []:
        key = tag.get("Key")
        value = tag.get("Value")
        if key is not None and value is not None:
            result[str(key)] = str(value)
    return result


def _is_protected(tags: dict[str, str]) -> bool:
    """Return True when the resource is allowed to keep running."""
    keep_value = tags.get(KEEP_TAG_KEY, "").lower()
    env_value = tags.get(ENV_TAG_KEY, "").lower()
    return keep_value == KEEP_TAG_VALUE.lower() or env_value == ENV_TAG_VALUE.lower()


def _scan_and_stop_ec2() -> list[dict[str, Any]]:
    ec2 = boto3.client("ec2")
    stopped: list[dict[str, Any]] = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": sorted(EC2_RUNNING_STATES)}]
    ):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                state = instance.get("State", {}).get("Name", "unknown")
                tags = _normalise_tags(instance.get("Tags"))

                if _is_protected(tags):
                    LOGGER.info("Skipping protected EC2 instance %s", instance_id)
                    continue

                LOGGER.warning(
                    "Stopping EC2 instance %s because it is missing %s=%s or %s=%s",
                    instance_id,
                    KEEP_TAG_KEY,
                    KEEP_TAG_VALUE,
                    ENV_TAG_KEY,
                    ENV_TAG_VALUE,
                )
                if not DRY_RUN:
                    ec2.stop_instances(InstanceIds=[instance_id])
                stopped.append(
                    {
                        "service": "ec2",
                        "resource_id": instance_id,
                        "previous_state": state,
                        "action": "dry-run" if DRY_RUN else "stopped",
                    }
                )

    return stopped


def _scan_and_stop_rds() -> list[dict[str, Any]]:
    rds = boto3.client("rds")
    stopped: list[dict[str, Any]] = []

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            db_id = db["DBInstanceIdentifier"]
            db_arn = db["DBInstanceArn"]
            state = db.get("DBInstanceStatus", "unknown")

            if state not in RDS_RUNNING_STATES:
                continue

            tags_response = rds.list_tags_for_resource(ResourceName=db_arn)
            tags = _normalise_tags(tags_response.get("TagList"))

            if _is_protected(tags):
                LOGGER.info("Skipping protected RDS instance %s", db_id)
                continue

            LOGGER.warning(
                "Stopping RDS instance %s because it is missing %s=%s or %s=%s",
                db_id,
                KEEP_TAG_KEY,
                KEEP_TAG_VALUE,
                ENV_TAG_KEY,
                ENV_TAG_VALUE,
            )
            if not DRY_RUN:
                rds.stop_db_instance(DBInstanceIdentifier=db_id)
            stopped.append(
                {
                    "service": "rds",
                    "resource_id": db_id,
                    "previous_state": state,
                    "action": "dry-run" if DRY_RUN else "stopped",
                }
            )

    return stopped


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    LOGGER.info("Cost Guard invoked with event: %s", json.dumps(event, default=str))

    stopped: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for scanner_name, scanner in (
        ("ec2", _scan_and_stop_ec2),
        ("rds", _scan_and_stop_rds),
    ):
        try:
            stopped.extend(scanner())
        except ClientError as exc:
            LOGGER.exception("%s scan failed", scanner_name)
            errors.append(
                {
                    "service": scanner_name,
                    "error_code": exc.response.get("Error", {}).get("Code", "ClientError"),
                    "message": exc.response.get("Error", {}).get("Message", str(exc)),
                }
            )

    status_code = 207 if errors else 200
    body = {"dry_run": DRY_RUN, "stopped_count": len(stopped), "stopped": stopped, "errors": errors}
    LOGGER.info("Cost Guard result: %s", json.dumps(body, default=str))

    return {"statusCode": status_code, "body": json.dumps(body)}
