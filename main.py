# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timezone
import os
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
import uvicorn

# Setup FastAPI app
app = FastAPI(title="Dropbox Clone API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# local s3_config
S3_BUCKET = "dropbox-bucket"
S3_ENDPOINT = "http://172.17.0.2:9000"
S3_ACCESS_KEY = "oQuC9BdxQUVxcfEUwj5H"
S3_SECRET_KEY = "veWW4IKZon58hEG6NWXWFwiwpt4pw0VWWc6LUNEX"

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

# type of files
ALLOWED_EXTENSIONS = {".txt", ".jpg", ".jpeg", ".png", ".json", ".pdf"}


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

@app.post("/api/upload/")
async def upload_file(file: UploadFile = File(...)):

    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="File type not allowed")
    

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    try:
    
        s3_client.upload_fileobj(file.file, S3_BUCKET, unique_filename)
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="S3 credentials not available")
    
    return {
        "filename": file.filename,
        "file_type": file_extension,
        "file_size": file.spool_max_size,
        "uploaded_at": datetime.now(timezone.utc)
    }

@app.get("/api/files/")
async def list_files():
    print('hi')
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        if 'Contents' not in response:
            return {"files": []}
        
        files = [obj['Key'] for obj in response['Contents']]
        return {"files": files}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="S3 credentials not available")

@app.get("/api/file/{file_id}")
async def download_file(file_id: str):
    file_path = f"s3://{S3_BUCKET}/{file_id}"
    
    return FileResponse(
        path=file_path, 
        filename=file_id,
        media_type="application/octet-stream"
    )

# root path
@app.get("/")
async def root():
    return {"message": "Dropbox Clone API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
