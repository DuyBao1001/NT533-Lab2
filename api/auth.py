import requests
from config import IDENTITY_URL

def get_token(username, password, project_name, domain_name="Default"):
    auth_url = f"{IDENTITY_URL}/auth/tokens"
    
    payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "domain": {"name": domain_name},
                        "password": password
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {"name": domain_name},
                    "name": project_name
                }
            }
        }
    }
    
    try:
        response = requests.post(auth_url, json=payload, timeout=10)
        
        if response.status_code == 201:
            return response.headers.get('X-Subject-Token'), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
            
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"

        return None, f"Lỗi kết nối: {str(e)}"