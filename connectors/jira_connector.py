import os
import requests
from requests.auth import HTTPBasicAuth


def fetch_jira():

    enabled = (
        os.getenv(
            "ENABLE_JIRA",
            "false"
        )
        .lower()
    )

    if enabled != "true":
        return []

    url = os.getenv(
        "JIRA_URL"
    )

    user = os.getenv(
        "JIRA_USER"
    )

    token = os.getenv(
        "JIRA_TOKEN"
    )

    project = os.getenv(
        "JIRA_PROJECT"
    )

    response = (
        requests.get(
            url,
            params={
                "jql":
                f"project={project}"
            },
            auth=
            HTTPBasicAuth(
                user,
                token
            )
        )
    )

    if response.status_code != 200:
        return []

    issues = (
        response
        .json()
        .get(
            "issues",
            []
        )
    )

    records=[]

    for i in issues:

        fields = (
            i.get(
                "fields",
                {}
            )
        )

        records.append({

            "id":
            i["key"],

            "incident":
            fields.get(
                "summary",
                ""
            ),

            "resolution":
            str(
                fields
            )

        })

    return records
