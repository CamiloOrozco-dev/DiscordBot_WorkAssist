import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("GITLAB_WEBHOOK_PORT", 5000)
SECRET = os.getenv("GITLAB_WEBHOOK_SECRET")
URL = f"http://localhost:{PORT}/gitlab"

def send_push_event():
    payload = {
        "object_kind": "push",
        "event_name": "push",
        "ref": "refs/heads/main",
        "user_name": "ZoroBot Tester",
        "project": {
            "name": "Test project",
            "path_with_namespace": "cite-lite/cite-bridge"
        },
        "commits": [
            {
                "id": "b6568db1bcfl",
                "message": "Update README.md\n\nMore details...",
                "url": "https://gitlab.com/test/project/-/commit/b6568db1bcfl",
                "author": {"name": "Tester"}
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Gitlab-Event": "Push Hook"
    }
    
    if SECRET:
        headers["X-Gitlab-Token"] = SECRET
        
    print(f"Enviando Push event a {URL}...")
    try:
        response = requests.post(URL, json=payload, headers=headers)
        print(f"Respuesta: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

def send_mr_event():
    payload = {
        "object_kind": "merge_request",
        "user": {"name": "Master Coder"},
        "project": {
            "name": "Awesome Project",
            "path_with_namespace": "transitel-movus/CTTB_Console_App"
        },
        "object_attributes": {
            "title": "Add New Feature",
            "url": "https://gitlab.com/test/project/-/merge_requests/1",
            "state": "opened",
            "action": "open",
            "source_branch": "feature/cool-stuff",
            "target_branch": "main"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Gitlab-Event": "Merge Request Hook"
    }
    
    if SECRET:
        headers["X-Gitlab-Token"] = SECRET
        
    print(f"Enviando Merge Request event a {URL}...")
    try:
        response = requests.post(URL, json=payload, headers=headers)
        print(f"Respuesta: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "push":
            send_push_event()
        elif sys.argv[1] == "mr":
            send_mr_event()
    else:
        send_push_event()
        send_mr_event()
