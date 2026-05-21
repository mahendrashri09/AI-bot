import json
import sys
import os
import pysqlite3
sys.modules["sqlite3"] = pysqlite3
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import requests
from requests.auth import HTTPBasicAuth

# ------------------------------
# Fetch RCA incidents from Jira
# ------------------------------
def fetch_jira_incidents():
    url = "https://<company>.atlassian.net/rest/api/3/search/jql"
    username = os.getenv("JIRA_USER")       # Export at runtime
    api_token = os.getenv("JIRA_TOKEN")     # Export at runtime

    jql = 'project = CLOUDOPS AND labels = RCA AND summary ~ "RCA - Testing"'
    params = {
        "jql": jql,
        "maxResults": 5,
        "fields": "*all"
    }
    headers = {"Accept": "application/json"}

    response = requests.get(
        url,
        headers=headers,
        params=params,
        auth=HTTPBasicAuth(username, api_token)
        # proxies can be added here if needed
    )

    jira_incidents = []
    if response.status_code == 200:
        issues = response.json().get("issues", [])
        for issue in issues:
            fields = issue.get("fields", {})
            # Extract description text if it's structured
            description = ""
            desc = fields.get("description")
            if isinstance(desc, dict) and desc.get("type") == "doc":
                for block in desc.get("content", []):
                    if "content" in block:
                        for c in block["content"]:
                            if "text" in c:
                                description += c["text"] + "\n"
            elif isinstance(desc, str):
                description = desc

            # Comments
            comments_text = ""
            comments = fields.get("comment", {}).get("comments", [])
            for c in comments:
                body = c.get("body")
                if isinstance(body, dict) and body.get("type") == "doc":
                    for block in body.get("content", []):
                        if "content" in block:
                            for txt in block["content"]:
                                if "text" in txt:
                                    comments_text += txt["text"] + "\n"
                elif isinstance(body, str):
                    comments_text += body + "\n"

            jira_incidents.append({
                "id": f"jira-{issue.get('key')}",
                "incident": f"{fields.get('summary','')}\n{description}\n{comments_text}",
                "resolution": comments_text.strip(),
                "service_name": fields.get("project", {}).get("key"),
                "severity": fields.get("priority", {}).get("name", "unknown"),
                "tags": ["jira"] + fields.get("labels", [])
            })
    else:
        print(f"Error fetching Jira tickets: {response.status_code} - {response.text}")

    return jira_incidents

# ------------------------------
# Initialize VectorDB with JSON + Jira
# ------------------------------
def init_vector_db():
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("incidents")
    except:
        collection = client.create_collection("incidents")

    existing_ids = set(collection.get()["ids"])

    # Load local incidents.json
    with open("incidents.json") as f:
        data = json.load(f)
    for item in data:
        if item["id"] not in existing_ids:
            collection.add(
                documents=[item["incident"] + " " + item["resolution"]],
                metadatas=[{"resolution": item["resolution"]}],
                ids=[item["id"]]
            )

    # Load Jira incidents
    jira_data = fetch_jira_incidents()
    for item in jira_data:
        if item["id"] not in existing_ids:
            collection.add(
                documents=[item["incident"]],
                metadatas=[{
                    "resolution": item.get("resolution"),
                    "service_name": item.get("service_name"),
                    "severity": item.get("severity"),
                    "tags": ",".join(item.get("tags", []))  # <-- convert list to string
                }],
                ids=[item["id"]]
            )
    return collection

# ------------------------------
# Query AI Copilot
# ------------------------------
def query_copilot(log_input, collection):
    # Step 1: Search VectorDB
    results = collection.query(
        query_texts=[log_input],
        n_results=2
    )
    context = ""
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context += f"Past Incident: {doc}\nResolution: {meta['resolution']}\n\n"

    # Step 2: Ask LLM via OpenAI-style client
    client = OpenAI(
        base_url=os.getenv("LITELLM_API_BASE"),
        api_key=os.getenv("LITELLM_API_KEY")
    )

    messages = [
        {"role": "system", "content": "You are an AI Incident Copilot for SREs. Summarize logs, match with past incidents, and suggest fixes."},
        {"role": "user", "content": f"Logs: {log_input}\n\nRelevant Incidents:\n{context}\n\nSuggest a fix."}
    ]

    try:
        chat_completion = client.chat.completions.create(
            model="gemini-2.5-flash-lite",
            messages=messages
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"An error occurred while querying the AI: {e}"

# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    collection = init_vector_db()
    test_log = "DB_CONN_TIMEOUT error observed in Payment Service during peak hours"
    suggestion = query_copilot(test_log, collection)
    print("AI Copilot Suggestion:\n", suggestion)

