import os

from openai import OpenAI

from connectors.local_connector import load_local

from connectors.jira_connector import fetch_jira


def build_context():

    local = (
        load_local()
    )

    jira = (
        fetch_jira()
    )

    all_items = (
        local
        +
        jira
    )

    context=[]

    for x in all_items:

        context.append(

            f'''
Incident:
{x["incident"]}

Resolution:
{x["resolution"]}
'''
        )

    return "\n".join(
        context
    )


def analyze(
    logs
):

    context = (
        build_context()
    )

    client = OpenAI(

        base_url=
        os.getenv(
            "LITELLM_API_BASE"
        ),

        api_key=
        os.getenv(
            "LITELLM_API_KEY"
        )

    )

    prompt = f'''

Analyze:

{logs}

Historical Incidents:

{context}

Return:

Summary

Matched Incidents

Confidence

Suggested Fix

References

'''

    result = (
        client
        .chat
        .completions
        .create(

            model=
            os.getenv(
                "MODEL_NAME"
            ),

            messages=[

                {
                    "role":
                    "user",

                    "content":
                    prompt
                }

            ]
        )
    )

    return (
        result
        .choices[0]
        .message
        .content
    )
