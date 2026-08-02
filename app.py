from flask import Flask, render_template, request, jsonify
import requests
import os
import json
import base64
import io
import mimetypes
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

# ===== KONFIGURASI =====
CRAZYROUTER_API_KEY = os.getenv('CRAZYROUTER_API_KEY')
API_HOST            = os.getenv('API_HOST', 'https://api.crazyrouter.com/v1')
AI_MODEL            = os.getenv('AI_MODEL', 'claude-opus-4-8')
GITHUB_TOKEN        = os.getenv('GITHUB_TOKEN')
GITHUB_REPO         = os.getenv('GITHUB_REPO', 'widodobudi/claude-chat-app')
GOOGLE_CREDS_JSON   = os.getenv('GOOGLE_CREDENTIALS_JSON')
RAILWAY_API_TOKEN   = os.getenv('RAILWAY_API_TOKEN')

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'md', 'py', 'js', 'html', 'css', 'json'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

conversation_history = []

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = '''Kamu adalah Claude AI assistant yang berjalan di web app dengan akses penuh ke:

🔧 **CAPABILITIES:**

1. **GitHub Repository** (widodobudi/claude-chat-app)
   - ✅ List semua file di repo
   - ✅ Baca konten file (code, markdown, json, dll)
   - ✅ Edit/update file (auto-commit)
   - ✅ Hapus file
   - ✅ Auto-save chat history setiap 20 pesan

2. **Google Drive** (via Service Account) - FULL CRUD!
   - ✅ List file & folder (read)
   - ✅ Upload file baru (create)
   - ✅ Download/baca file (read)
   - ✅ Edit/update file content (update)
   - ✅ Hapus file (delete)
   - ✅ Append/tambah content ke file existing
   - NOTE: User harus share folder/file dengan service account

3. **Railway Platform** (Deployment Management)
   - ✅ List semua projects
   - ✅ List services dalam project
   - ✅ Lihat deployment history & status
   - ✅ Trigger redeploy/restart service
   - ⚠️ Deploy logs detail → arahkan user ke Railway Dashboard

4. **Vision & Multimodal**
   - ✅ Bisa melihat dan menganalisis gambar yang di-paste/upload user
   - ✅ Bisa membaca file text, code, markdown, JSON
   - ✅ Bisa memproses multiple images sekaligus

📌 **IMPORTANT RULES:**
- Kamu BISA dan AKTIF menggunakan tools/functions yang tersedia
- Saat user minta lihat/edit file → langsung gunakan tools
- Saat user minta upload/edit Google Drive → gunakan drive_upload/drive_update
- Saat user minta cek deploy status → gunakan get_railway_deployments()
- Saat user minta lihat deploy logs detail → kasih tau harus ke Railway Dashboard
- Saat user minta deploy/restart → gunakan railway_redeploy()
- Saat user paste/upload gambar → analisis dan jelaskan
- Selalu konfirmasi sebelum melakukan operasi destructive (hapus, edit, deploy)
- Jawab dalam bahasa yang sama dengan user
- Be proactive, helpful, and efficient!

🎯 **EXAMPLES:**
- "Upload file ini ke Google Drive" → gunakan drive_upload()
- "Edit file X di Drive, tambahkan Y" → gunakan drive_update()
- "Cek status deploy terbaru" → gunakan get_railway_deployments()
- "Kenapa deploy gagal?" → cek deployment history, kasih status, arahkan ke Railway Dashboard untuk logs detail
- "Deploy ulang Railway" → gunakan railway_redeploy()
- User paste screenshot → "Saya lihat di gambar ini ada..."

Kamu memiliki akses penuh untuk membantu user mengelola code, files, dan deployment mereka!'''

# ===== TOOLS DEFINITION =====
TOOLS = [
    # GitHub Tools
    {
        "name": "get_github_files",
        "description": "List semua file dan folder di GitHub repository. Menampilkan struktur directory lengkap.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_github_file",
        "description": "Membaca konten dari file spesifik di GitHub repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path file relatif dari root repo, contoh: 'app.py' atau 'templates/index.html'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "update_github_file",
        "description": "Edit/update konten file di GitHub repository. Akan auto-commit dengan pesan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path file yang akan diupdate"
                },
                "content": {
                    "type": "string",
                    "description": "Konten baru file (full content, bukan diff)"
                },
                "message": {
                    "type": "string",
                    "description": "Commit message"
                }
            },
            "required": ["path", "content", "message"]
        }
    },
    {
        "name": "delete_github_file",
        "description": "Hapus file dari GitHub repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path file yang akan dihapus"
                }
            },
            "required": ["path"]
        }
    },
    # Google Drive Tools
    {
        "name": "get_drive_files",
        "description": "List file dan folder di Google Drive (20 file terbaru)",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "drive_upload",
        "description": "Upload file baru ke Google Drive atau create text file baru",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Nama file yang akan dibuat"
                },
                "content": {
                    "type": "string",
                    "description": "Konten file (untuk text file)"
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type file, contoh: 'text/plain', 'application/json', 'text/html'"
                }
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "drive_read",
        "description": "Baca konten file dari Google Drive",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID file di Google Drive"
                }
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "drive_update",
        "description": "Update/edit konten file existing di Google Drive",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID file di Google Drive yang akan diupdate"
                },
                "content": {
                    "type": "string",
                    "description": "Konten baru file (full content replacement)"
                }
            },
            "required": ["file_id", "content"]
        }
    },
    {
        "name": "drive_append",
        "description": "Append/tambahkan content ke file existing di Google Drive (tidak replace, tapi tambah di akhir)",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID file di Google Drive"
                },
                "content": {
                    "type": "string",
                    "description": "Konten yang akan ditambahkan di akhir file"
                }
            },
            "required": ["file_id", "content"]
        }
    },
    {
        "name": "drive_delete",
        "description": "Hapus file dari Google Drive",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID file di Google Drive yang akan dihapus"
                }
            },
            "required": ["file_id"]
        }
    },
    # Railway Tools
    {
        "name": "get_railway_projects",
        "description": "List semua project di Railway account",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_railway_services",
        "description": "List semua service dalam Railway project tertentu",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "ID project Railway"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "get_railway_deployments",
        "description": "List deployment history dari Railway service tertentu (10 deployment terbaru). Menampilkan status (SUCCESS/FAILED/BUILDING) dan timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {
                    "type": "string",
                    "description": "ID service Railway"
                }
            },
            "required": ["service_id"]
        }
    },
    {
        "name": "railway_redeploy",
        "description": "Trigger redeploy/restart service di Railway",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {
                    "type": "string",
                    "description": "ID service Railway yang akan di-redeploy"
                }
            },
            "required": ["service_id"]
        }
    }
]

# ===== FUNCTION EXECUTORS =====
def execute_tool(tool_name, tool_input):
    """Execute tool dan return hasilnya"""
    try:
        # GitHub tools
        if tool_name == "get_github_files":
            return get_github_files_internal()
        elif tool_name == "get_github_file":
            return get_github_file_internal(tool_input['path'])
        elif tool_name == "update_github_file":
            return update_github_file_internal(
                tool_input['path'],
                tool_input['content'],
                tool_input['message']
            )
        elif tool_name == "delete_github_file":
            return delete_github_file_internal(tool_input['path'])
        
        # Google Drive tools
        elif tool_name == "get_drive_files":
            return get_drive_files_internal()
        elif tool_name == "drive_upload":
            return drive_upload_internal(
                tool_input['filename'],
                tool_input['content'],
                tool_input.get('mime_type', 'text/plain')
            )
        elif tool_name == "drive_read":
            return drive_read_internal(tool_input['file_id'])
        elif tool_name == "drive_update":
            return drive_update_internal(
                tool_input['file_id'],
                tool_input['content']
            )
        elif tool_name == "drive_append":
            return drive_append_internal(
                tool_input['file_id'],
                tool_input['content']
            )
        elif tool_name == "drive_delete":
            return drive_delete_internal(tool_input['file_id'])
        
        # Railway tools
        elif tool_name == "get_railway_projects":
            return get_railway_projects_internal()
        elif tool_name == "get_railway_services":
            return get_railway_services_internal(tool_input['project_id'])
        elif tool_name == "get_railway_deployments":
            return get_railway_deployments_internal(tool_input['service_id'])
        elif tool_name == "railway_redeploy":
            return railway_redeploy_internal(tool_input['service_id'])
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": str(e)}

# ===== GITHUB INTERNAL FUNCTIONS =====
def get_github_files_internal():
    """List all files in repo"""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/git/trees/main?recursive=1'
        response = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        })
        if response.status_code == 200:
            tree = response.json().get('tree', [])
            files = [item for item in tree if item['type'] == 'blob']
            return {
                "total_files": len(files),
                "files": [{"path": f['path'], "size": f.get('size', 0)} for f in files]
            }
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_github_file_internal(path):
    """Read file content from GitHub"""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
        response = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        })
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return {
                "path": path,
                "size": data['size'],
                "content": content
            }
        return {"error": f"File not found or GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def update_github_file_internal(path, content, message):
    """Update file in GitHub"""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
        response = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        })
        
        sha = None
        if response.status_code == 200:
            sha = response.json()['sha']
        
        encoded_content = base64.b64encode(content.encode()).decode()
        payload = {
            'message': message,
            'content': encoded_content
        }
        if sha:
            payload['sha'] = sha
        
        response = requests.put(url, 
            headers={
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            },
            json=payload
        )
        
        if response.status_code in [200, 201]:
            return {"success": True, "message": f"File {path} updated successfully"}
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def delete_github_file_internal(path):
    """Delete file from GitHub"""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
        response = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        })
        
        if response.status_code != 200:
            return {"error": "File not found"}
        
        sha = response.json()['sha']
        
        response = requests.delete(url,
            headers={
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            },
            json={
                'message': f'Delete {path}',
                'sha': sha
            }
        )
        
        if response.status_code == 200:
            return {"success": True, "message": f"File {path} deleted"}
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ===== GOOGLE DRIVE INTERNAL FUNCTIONS =====
def get_drive_service():
    """Get Google Drive service"""
    if not GOOGLE_CREDS_JSON:
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
        
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error creating Drive service: {e}")
        return None

def get_drive_files_internal():
    """List Google Drive files"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        results = service.files().list(
            pageSize=20,
            fields="files(id, name, mimeType, size, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()
        files = results.get('files', [])
        return {
            "total": len(files),
            "files": files
        }
    except Exception as e:
        return {"error": str(e)}

def drive_upload_internal(filename, content, mime_type='text/plain'):
    """Upload new file to Google Drive"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        from googleapiclient.http import MediaIoBaseUpload
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode('utf-8')),
            mimetype=mime_type,
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size'
        ).execute()
        
        return {
            "success": True,
            "file_id": file.get('id'),
            "filename": file.get('name'),
            "size": file.get('size'),
            "message": f"File '{filename}' uploaded successfully"
        }
    except Exception as e:
        return {"error": str(e)}

def drive_read_internal(file_id):
    """Read file content from Google Drive"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        from googleapiclient.http import MediaIoBaseDownload
        
        file = service.files().get(fileId=file_id, fields='name, mimeType, size').execute()
        
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        content = fh.getvalue().decode('utf-8')
        
        return {
            "success": True,
            "filename": file.get('name'),
            "mime_type": file.get('mimeType'),
            "size": file.get('size'),
            "content": content
        }
    except Exception as e:
        return {"error": str(e)}

def drive_update_internal(file_id, content):
    """Update file content in Google Drive (full replacement)"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        from googleapiclient.http import MediaIoBaseUpload
        
        file = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode('utf-8')),
            mimetype=file.get('mimeType', 'text/plain'),
            resumable=True
        )
        
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields='id, name, size, modifiedTime'
        ).execute()
        
        return {
            "success": True,
            "file_id": updated_file.get('id'),
            "filename": updated_file.get('name'),
            "size": updated_file.get('size'),
            "modified": updated_file.get('modifiedTime'),
            "message": f"File '{file.get('name')}' updated successfully"
        }
    except Exception as e:
        return {"error": str(e)}

def drive_append_internal(file_id, append_content):
    """Append content to existing file in Google Drive"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        read_result = drive_read_internal(file_id)
        if "error" in read_result:
            return read_result
        
        existing_content = read_result.get('content', '')
        new_content = existing_content + append_content
        
        return drive_update_internal(file_id, new_content)
        
    except Exception as e:
        return {"error": str(e)}

def drive_delete_internal(file_id):
    """Delete file from Google Drive"""
    service = get_drive_service()
    if not service:
        return {"error": "Google Drive not configured"}
    try:
        file = service.files().get(fileId=file_id, fields='name').execute()
        filename = file.get('name')
        
        service.files().delete(fileId=file_id).execute()
        
        return {
            "success": True,
            "message": f"File '{filename}' deleted successfully"
        }
    except Exception as e:
        return {"error": str(e)}

# ===== RAILWAY INTERNAL FUNCTIONS =====
def get_railway_projects_internal():
    """List Railway projects"""
    if not RAILWAY_API_TOKEN:
        return {"error": "Railway API token not configured"}
    
    query = """
    query {
      projects {
        edges {
          node {
            id
            name
            description
          }
        }
      }
    }
    """
    
    try:
        res = requests.post(
            'https://backboard.railway.app/graphql/v2',
            headers={
                'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={'query': query}
        )
        
        if res.status_code == 200:
            data = res.json()
            projects = [edge['node'] for edge in data.get('data', {}).get('projects', {}).get('edges', [])]
            return {"projects": projects}
        return {"error": f"Railway API error: {res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_railway_services_internal(project_id):
    """List services in Railway project"""
    if not RAILWAY_API_TOKEN:
        return {"error": "Railway API token not configured"}
    
    query = """
    query project($id: String!) {
      project(id: $id) {
        services {
          edges {
            node {
              id
              name
            }
          }
        }
      }
    }
    """
    
    try:
        res = requests.post(
            'https://backboard.railway.app/graphql/v2',
            headers={
                'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'query': query,
                'variables': {'id': project_id}
            }
        )
        
        if res.status_code == 200:
            data = res.json()
            services = [edge['node'] for edge in 
                       data.get('data', {}).get('project', {}).get('services', {}).get('edges', [])]
            return {"services": services}
        return {"error": f"Railway API error: {res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_railway_deployments_internal(service_id):
    """List deployment history dari Railway service"""
    if not RAILWAY_API_TOKEN:
        return {"error": "Railway API token not configured"}
    
    query = """
    query service($id: String!) {
      service(id: $id) {
        deployments(first: 10) {
          edges {
            node {
              id
              status
              createdAt
            }
          }
        }
      }
    }
    """
    
    try:
        res = requests.post(
            'https://backboard.railway.app/graphql/v2',
            headers={
                'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'query': query,
                'variables': {'id': service_id}
            }
        )
        
        if res.status_code == 200:
            data = res.json()
            deployments = [edge['node'] for edge in 
                          data.get('data', {}).get('service', {}).get('deployments', {}).get('edges', [])]
            
            return {
                "success": True,
                "total": len(deployments),
                "deployments": deployments,
                "note": "Untuk melihat logs detail dari deployment, akses Railway Dashboard → Service → Deploy Logs tab"
            }
        return {"error": f"Railway API error: {res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def railway_redeploy_internal(service_id):
    """Redeploy Railway service"""
    if not RAILWAY_API_TOKEN:
        return {"error": "Railway API token not configured"}
    
    mutation = """
    mutation serviceInstanceRedeploy($serviceId: String!) {
      serviceInstanceRedeploy(serviceId: $serviceId)
    }
    """
    
    try:
        res = requests.post(
            'https://backboard.railway.app/graphql/v2',
            headers={
                'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'query': mutation,
                'variables': {'serviceId': service_id}
            }
        )
        
        if res.status_code == 200:
            return {"success": True, "message": "Service redeployed successfully"}
        return {"error": f"Railway API error: {res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ===== HELPER: Save chat to GitHub =====
def save_chat_to_github(history):
    """Auto-commit history chat ke GitHub"""
    if not GITHUB_TOKEN:
        return False
    try:
        timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename   = f'chat_history/chat_{timestamp}.json'
        content    = base64.b64encode(
            json.dumps(history, indent=2, ensure_ascii=False).encode()
        ).decode()
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}'
        requests.put(url,
            headers={
                'Authorization': f'token {GITHUB_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'message': f'💬 Chat saved: {timestamp}',
                'content': content
            }
        )
        return True
    except:
        return False

# ===== MAIN CHAT ROUTE WITH FUNCTION CALLING =====
@app.route('/chat', methods=['POST'])
def chat():
    global conversation_history
    data = request.json
    message = data.get('message', '').strip()
    attachments = data.get('attachments', [])
    
    if not message and not attachments:
        return jsonify({'error': 'Pesan kosong'}), 400
    
    # Build message content (support multimodal)
    message_content = []
    
    if message:
        message_content.append({
            'type': 'text',
            'text': message
        })
    
    for attachment in attachments:
        if attachment.get('type') == 'image':
            message_content.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': attachment['mime_type'],
                    'data': attachment['data']
                }
            })
        elif attachment.get('type') == 'text':
            message_content.append({
                'type': 'text',
                'text': f"\n\n📄 **File: {attachment['filename']}**\n```\n{attachment['content']}\n```"
            })
    
    if len(message_content) == 1 and message_content[0]['type'] == 'text':
        conversation_history.append({
            'role': 'user',
            'content': message
        })
    else:
        conversation_history.append({
            'role': 'user',
            'content': message_content
        })
    
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            response = requests.post(
                f"{API_HOST}/messages",
                headers={
                    'x-api-key': CRAZYROUTER_API_KEY,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': AI_MODEL,
                    'max_tokens': 4096,
                    'system': SYSTEM_PROMPT,
                    'messages': conversation_history,
                    'tools': TOOLS
                },
                timeout=60
            )
            
            if response.status_code != 200:
                return jsonify({'error': f'API Error {response.status_code}'}), 500
            
            result = response.json()
            assistant_message = {
                'role': 'assistant',
                'content': result['content']
            }
            conversation_history.append(assistant_message)
            
            stop_reason = result.get('stop_reason')
            
            if stop_reason == 'tool_use':
                tool_results = []
                
                for block in result['content']:
                    if block['type'] == 'tool_use':
                        tool_name = block['name']
                        tool_input = block['input']
                        tool_use_id = block['id']
                        
                        print(f"🔧 Executing tool: {tool_name} with input: {tool_input}")
                        
                        tool_result = execute_tool(tool_name, tool_input)
                        
                        tool_results.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_use_id,
                            'content': json.dumps(tool_result, ensure_ascii=False)
                        })
                
                conversation_history.append({
                    'role': 'user',
                    'content': tool_results
                })
                
                continue
            
            elif stop_reason == 'end_turn':
                reply_text = ""
                for block in result['content']:
                    if block['type'] == 'text':
                        reply_text += block['text']
                
                if len(conversation_history) % 20 == 0:
                    save_chat_to_github(conversation_history)
                
                if len(conversation_history) > 50:
                    conversation_history = conversation_history[-50:]
                
                return jsonify({
                    'reply': reply_text,
                    'model': AI_MODEL
                })
            
            else:
                reply_text = ""
                for block in result['content']:
                    if block['type'] == 'text':
                        reply_text += block['text']
                
                return jsonify({
                    'reply': reply_text or "Response completed",
                    'model': AI_MODEL
                })
        
        except requests.Timeout:
            return jsonify({'error': 'Request timeout'}), 504
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Max iterations reached'}), 500

# ===== UPLOAD ROUTE =====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload (image, text, etc)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({'error': 'File too large (max 10MB)'}), 400
            
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            file.save(filepath)
            
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                with open(filepath, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                    mime_type = f"image/{file_ext if file_ext != 'jpg' else 'jpeg'}"
                
                return jsonify({
                    'type': 'image',
                    'filename': filename,
                    'mime_type': mime_type,
                    'data': image_data,
                    'size': file_size
                })
            
            elif file_ext in ['txt', 'md', 'py', 'js', 'html', 'css', 'json']:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return jsonify({
                    'type': 'text',
                    'filename': filename,
                    'content': content,
                    'size': file_size
                })
            
            else:
                return jsonify({
                    'type': 'file',
                    'filename': filename,
                    'size': file_size,
                    'path': filepath
                })
        
        return jsonify({'error': 'File type not allowed'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== OTHER ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clear', methods=['POST'])
def clear():
    global conversation_history
    if conversation_history:
        save_chat_to_github(conversation_history)
    conversation_history = []
    return jsonify({'status': 'cleared'})

@app.route('/config', methods=['GET'])
def config():
    return jsonify({
        'model': AI_MODEL,
        'github': bool(GITHUB_TOKEN),
        'drive': bool(GOOGLE_CREDS_JSON),
        'railway': bool(RAILWAY_API_TOKEN)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
