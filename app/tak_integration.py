import requests
import logging

logger = logging.getLogger(__name__)

class TAKServerAPI:
    def __init__(self, api_url, admin_user, admin_pass):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = (admin_user, admin_pass)
        self.session.verify = False
    
    def create_user(self, username, password):
        try:
            response = self.session.post(f"{self.api_url}/users", 
                json={"name": username, "password": password}, timeout=10)
            response.raise_for_status()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
