import os
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

load_dotenv()
security = HTTPBasic()

XEZA_PASS = os.getenv("XEZA_PASS", "mypass123")

def verify_credentials(credentials: HTTPBasicCredentials = security):
    correct_username = "admin"
    if credentials.username != correct_username or credentials.password != XEZA_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Invalid Credentials for ORAKX Matrix",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username