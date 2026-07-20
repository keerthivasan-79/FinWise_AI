import os, secrets

BASE_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTANCE_DIR=os.path.join(BASE_DIR, 'instance')

def load_env_file():
    env_path=os.path.join(BASE_DIR,'.env')
    if not os.path.exists(env_path): return
    with open(env_path,encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            key,value=line.split('=',1)
            os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

def local_secret(name):
    os.makedirs(INSTANCE_DIR,exist_ok=True)
    path=os.path.join(INSTANCE_DIR,name)
    if os.path.exists(path):
        with open(path,encoding='utf-8') as f: return f.read().strip()
    value=secrets.token_urlsafe(48)
    with open(path,'w',encoding='utf-8') as f: f.write(value)
    return value

load_env_file()
DB_CONFIG={
 "host":os.getenv("DB_HOST","localhost"),
 "user":os.getenv("DB_USER","root"),
 "password":os.getenv("DB_PASSWORD",""),
 "database":os.getenv("DB_NAME","expense_manager_web")
}
JWT_SECRET=os.getenv("JWT_SECRET") or local_secret('jwt_secret.key')
ACCESS_TOKEN_MINUTES=int(os.getenv("ACCESS_TOKEN_MINUTES","30"))
REFRESH_TOKEN_DAYS=int(os.getenv("REFRESH_TOKEN_DAYS","30"))
MAX_UPLOAD_MB=int(os.getenv("MAX_UPLOAD_MB","8"))
COOKIE_SECURE=os.getenv("COOKIE_SECURE","false").lower()=="true"
