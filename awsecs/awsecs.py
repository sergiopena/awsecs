import boto3
from botocore import credentials
import botocore.session
from botocore.exceptions import (
    ClientError,
    ProfileNotFound,
    NoRegionError,
    EndpointConnectionError,
)


import sys
import os
import argparse
import re
import json
from pyfzf.pyfzf import FzfPrompt

# Use the credential cache path used by awscli
AWS_CREDENTIAL_CACHE_DIR = os.path.join(
    os.path.expanduser("~"), ".aws/cli/cache"
)


def build_aws_client(*args, **kwargs):
    """Build an AWS client using the awscli credential cache."""

    # Create a session with the credential cache
    session = botocore.session.get_session()
    provider = session.get_component("credential_provider").get_provider(
        "assume-role"
    )
    provider.cache = credentials.JSONFileCache(AWS_CREDENTIAL_CACHE_DIR)

    # Create boto3 client from session
    return boto3.Session(botocore_session=session).client(*args, **kwargs)


def get_clusters(args):
    try:
        ecsclient = build_aws_client("ecs", region_name=args.region)
        response = ecsclient.list_clusters()
        clusters = map(lambda x: x.split('/')[1], response.get('clusterArns'))
        return list(clusters)
    except ProfileNotFound as e:
        print(e.message)
        print(
            "Make sure you defined and env var AWS_PROFILE "
            "pointing to your credentials"
        )
        sys.exit(1)
    except NoRegionError as e:
        print(e.message)
        print("You need to define a region in your profile")
        sys.exit(1)
    except EndpointConnectionError as e:
        print(e.message)
        print("Check your region name, seems it's not reachable")
        sys.exit(1)
    except Exception:
        print("Unexpected error:", sys.exc_info()[0])
        raise

def get_tasks(args, cluster):
    containers = []
    try:
        ecsclient = build_aws_client("ecs", region_name=args.region)
        response = ecsclient.list_tasks(cluster=cluster)
        tasks = ecsclient.describe_tasks(cluster=cluster, tasks=response.get('taskArns'))
        for task in tasks.get('tasks'):
            task_name = task.get('taskDefinitionArn').split('/')[1]
            task_arn = task.get('taskArn').split('/')[2]

            for container in task.get('containers'):
                container_name = container.get('name')
                container_id = container.get('containerArn').split('/')[1]
                print(task_name, container_name, container_id)
                containers.append("{} - {} - {} - {}".format(task_name, task_arn, container_name, container_id))


        return containers

    except ProfileNotFound as e:
        print(e.message)
        print(
            "Make sure you defined and env var AWS_PROFILE "
            "pointing to your credentials"
        )
        sys.exit(1)
    except NoRegionError as e:
        print(e.message)
        print("You need to define a region in your profile")
        sys.exit(1)
    except EndpointConnectionError as e:
        print(e.message)
        print("Check your region name, seems it's not reachable")
        sys.exit(1)
    except Exception:
        print("Unexpected error:", sys.exc_info()[0])
        raise

def main():

    parser = argparse.ArgumentParser(
        description="AWS SSM console manager",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--region",
        "-r",
        default="eu-west-1",
        help="Region to retrieve instances from",
    )

    parser.add_argument(
        "--instanceId",
        "-i",
        required=False,
        help="Filter by instance id by applying .*arg.*",
    )

    parser.add_argument(
        "--name",
        "-n",
        required=False,
        help="Filter by instance name by applying .*arg.*",
    )

    parser.add_argument(
        "--address",
        "-a",
        required=False,
        help="IP address of the instance"
    )

    parser.add_argument(
        "--dryrun",
        "-d",
        action="store_true",
        required=False,
        help="Dry run, do not connec to the instance just list matchs"
    )

    args = parser.parse_args()
    clusters = get_clusters(args)
    fzf = FzfPrompt()
    cluster = fzf.prompt(clusters)
    print(cluster)
    tasks = get_tasks(args, cluster[0])
#    tasks = get_tasks(args, 'statsuite-iac-ecs-statsuiteclusterecscluster0A8E3C7D-xRKh1OrSpFwQ')
    task = fzf.prompt(tasks)
    print(task)
    taskId = task[0].split(" - ")[1]
    containerId = task[0].split(" - ")[2]
    os.execlp("aws", "aws", "ecs", "execute-command", "--cluster", cluster[0], "--task", taskId, "--container", containerId, "--command", "/bin/sh", "--interactive")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
