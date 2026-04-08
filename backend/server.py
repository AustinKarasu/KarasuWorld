from dotenv import load_dotenv
load_dotenv()

import socketio
from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os, json, logging, bcrypt, jwt, uuid, secrets, re, time, base64, hashlib, httpx
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

# MongoDB
mongo_url = os.environ['MONGO_URL']
db_client = AsyncIOMotorClient(mongo_url)
db = db_client[os.environ.get('DB_NAME', 'karasuworld')]

JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = "HS256"

# Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', logger=False, engineio_logger=False)
fastapi_app = FastAPI(title="KarasuWorld API")

online_users = {}
sid_user_map = {}

# ============ RATE LIMITING ============
rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT = CONFIG.get("security", {}).get("rate_limit_per_minute", 60)
MAX_MSG_LEN = CONFIG.get("security", {}).get("max_message_length", 4000)

def check_rate_limit(ip: str):
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < 60]
    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    rate_limit_store[ip].append(now)

def sanitize_input(text: str) -> str:
    if not text:
        return text
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()

# ============ DISCORD-LIKE PERMISSIONS ============
PERMISSIONS = {
    "administrator": 1 << 0,
    "manage_server": 1 << 1,
    "manage_channels": 1 << 2,
    "manage_roles": 1 << 3,
    "manage_members": 1 << 4,
    "kick_members": 1 << 5,
    "ban_members": 1 << 6,
    "send_messages": 1 << 7,
    "manage_messages": 1 << 8,
    "add_reactions": 1 << 9,
    "connect_voice": 1 << 10,
    "speak": 1 << 11,
    "mute_members": 1 << 12,
    "deafen_members": 1 << 13,
    "mention_everyone": 1 << 14,
    "attach_files": 1 << 15,
    "view_channels": 1 << 16,
}
DEFAULT_PERMISSIONS = sum([
    PERMISSIONS["send_messages"], PERMISSIONS["add_reactions"],
    PERMISSIONS["connect_voice"], PERMISSIONS["speak"],
    PERMISSIONS["attach_files"], PERMISSIONS["view_channels"],
])
ADMIN_PERMISSIONS = sum(PERMISSIONS.values())

def has_permission(user_permissions: int, perm_name: str) -> bool:
    if user_permissions & PERMISSIONS["administrator"]:
        return True
    return bool(user_permissions & PERMISSIONS.get(perm_name, 0))

# ============ MODELS ============
class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    session_id: str

class ServerCreate(BaseModel):
    name: str
    description: str = ""
    icon_letter: str = ""

class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "text"

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"
    media_url: str = ""
    media_type: str = ""

class DMCreate(BaseModel):
    recipient_id: str

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_base64: Optional[str] = None
    banner_base64: Optional[str] = None
    status: Optional[str] = None
    display_name: Optional[str] = None

class ReactionRequest(BaseModel):
    emoji: str

class JoinServerRequest(BaseModel):
    invite_code: str

class RoleCreate(BaseModel):
    name: str
    color: str = "#99AAB5"
    permissions: int = DEFAULT_PERMISSIONS
    position: int = 0

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    permissions: Optional[int] = None
    position: Optional[int] = None

class FriendRequestCreate(BaseModel):
    target_user_id: str

class PushTokenRegister(BaseModel):
    push_token: str
    device_type: str = "expo"

class E2EKeyExchange(BaseModel):
    public_key: str

class UploadRequest(BaseModel):
    data: str
    filename: str
    content_type: str = "image/png"

# ============ AUTH UTILITIES ============
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=30), "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    check_rate_limit(request.client.host if request.client else "unknown")
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        token = request.cookies.get("session_token")
        if token:
            session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
            if session:
                expires_at = session.get("expires_at")
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if expires_at and expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
                    if user:
                        user.pop("password_hash", None)
                        return user
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_user_server_permissions(user_id: str, server_id: str) -> int:
    server = await db.servers.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        return 0
    if server.get("owner_id") == user_id:
        return ADMIN_PERMISSIONS
    membership = await db.server_members.find_one({"server_id": server_id, "user_id": user_id}, {"_id": 0})
    if not membership:
        return 0
    role_ids = membership.get("role_ids", [])
    if membership.get("role") == "admin":
        return ADMIN_PERMISSIONS
    total_perms = DEFAULT_PERMISSIONS
    if role_ids:
        roles = await db.roles.find({"role_id": {"$in": role_ids}}, {"_id": 0}).to_list(50)
        for role in roles:
            total_perms |= role.get("permissions", 0)
    return total_perms

# ============ AUTH ROUTES ============
@fastapi_app.post("/api/auth/register")
async def register(req: RegisterRequest, request: Request):
    check_rate_limit(request.client.host if request.client else "unknown")
    email = sanitize_input(req.email.lower().strip())
    username = sanitize_input(req.username.strip())
    if not re.match(r'^[a-zA-Z0-9_.]{2,32}$', username):
        raise HTTPException(status_code=400, detail="Username must be 2-32 chars, alphanumeric or _ .")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if await db.users.find_one({"email": email}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": username}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id, "email": email, "username": username,
        "display_name": username,
        "password_hash": hash_password(req.password),
        "bio": "", "avatar_base64": "", "banner_base64": "",
        "status": "online", "custom_status": "",
        "role": "member",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    safe_user = {k: v for k, v in user_doc.items() if k not in ('_id', 'password_hash')}
    return {"user": safe_user, "access_token": access_token, "refresh_token": refresh_token}

@fastapi_app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    check_rate_limit(request.client.host if request.client else "unknown")
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(user["user_id"], email)
    refresh_token = create_refresh_token(user["user_id"])
    safe_user = {k: v for k, v in user.items() if k not in ('_id', 'password_hash')}
    return {"user": safe_user, "access_token": access_token, "refresh_token": refresh_token}

@fastapi_app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}

@fastapi_app.post("/api/auth/refresh")
async def refresh_token(request: Request):
    token = request.headers.get("X-Refresh-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"access_token": create_access_token(payload["sub"], user["email"])}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
@fastapi_app.post("/api/auth/google")
async def google_auth(req: GoogleAuthRequest):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": req.session_id}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google session")
            google_data = resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=500, detail="Failed to verify Google session")

    email = google_data.get("email", "").lower()
    name = google_data.get("name", email.split("@")[0])
    picture = google_data.get("picture", "")
    session_token = google_data.get("session_token", "")

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"display_name": name, "status": "online"}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id, "email": email, "username": name.replace(" ", "_").lower()[:32],
            "display_name": name, "password_hash": "",
            "bio": "", "avatar_base64": "", "banner_base64": "",
            "status": "online", "custom_status": "", "role": "member",
            "google_picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    if session_token:
        await db.user_sessions.update_one(
            {"session_token": session_token},
            {"$set": {
                "user_id": user_id, "session_token": session_token,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True
        )

    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": user, "access_token": access_token, "refresh_token": refresh_token}

# ============ FRIEND SYSTEM ============
@fastapi_app.post("/api/friends/request")
async def send_friend_request(req: FriendRequestCreate, user: dict = Depends(get_current_user)):
    if req.target_user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    target = await db.users.find_one({"user_id": req.target_user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    existing = await db.friendships.find_one({
        "$or": [
            {"user_id": user["user_id"], "friend_id": req.target_user_id},
            {"user_id": req.target_user_id, "friend_id": user["user_id"]},
        ]
    })
    if existing:
        if existing.get("status") == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        if existing.get("status") == "pending":
            raise HTTPException(status_code=400, detail="Friend request already pending")
    friendship_id = f"fr_{uuid.uuid4().hex[:12]}"
    await db.friendships.insert_one({
        "friendship_id": friendship_id,
        "user_id": user["user_id"], "friend_id": req.target_user_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await sio.emit('friend_request', {
        "friendship_id": friendship_id,
        "from_user": {"user_id": user["user_id"], "username": user["username"]},
    }, room=f"user_{req.target_user_id}")
    return {"friendship_id": friendship_id, "status": "pending"}

@fastapi_app.post("/api/friends/{friendship_id}/accept")
async def accept_friend(friendship_id: str, user: dict = Depends(get_current_user)):
    fr = await db.friendships.find_one({"friendship_id": friendship_id, "friend_id": user["user_id"], "status": "pending"})
    if not fr:
        raise HTTPException(status_code=404, detail="Friend request not found")
    await db.friendships.update_one({"friendship_id": friendship_id}, {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()}})
    return {"status": "accepted"}

@fastapi_app.post("/api/friends/{friendship_id}/decline")
async def decline_friend(friendship_id: str, user: dict = Depends(get_current_user)):
    fr = await db.friendships.find_one({"friendship_id": friendship_id, "friend_id": user["user_id"], "status": "pending"})
    if not fr:
        raise HTTPException(status_code=404, detail="Friend request not found")
    await db.friendships.delete_one({"friendship_id": friendship_id})
    return {"status": "declined"}

@fastapi_app.delete("/api/friends/{friendship_id}")
async def remove_friend(friendship_id: str, user: dict = Depends(get_current_user)):
    fr = await db.friendships.find_one({"friendship_id": friendship_id, "$or": [{"user_id": user["user_id"]}, {"friend_id": user["user_id"]}]})
    if not fr:
        raise HTTPException(status_code=404, detail="Friendship not found")
    await db.friendships.delete_one({"friendship_id": friendship_id})
    return {"status": "removed"}

@fastapi_app.get("/api/friends")
async def list_friends(user: dict = Depends(get_current_user)):
    friends = await db.friendships.find({
        "$or": [{"user_id": user["user_id"]}, {"friend_id": user["user_id"]}],
        "status": "accepted"
    }, {"_id": 0}).to_list(500)
    friend_ids = []
    for f in friends:
        fid = f["friend_id"] if f["user_id"] == user["user_id"] else f["user_id"]
        friend_ids.append(fid)
    if not friend_ids:
        return {"friends": []}
    users = await db.users.find({"user_id": {"$in": friend_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)
    user_map = {u["user_id"]: u for u in users}
    result = []
    for f in friends:
        fid = f["friend_id"] if f["user_id"] == user["user_id"] else f["user_id"]
        u = user_map.get(fid, {})
        result.append({
            "friendship_id": f["friendship_id"],
            "user_id": fid,
            "username": u.get("username", "Unknown"),
            "display_name": u.get("display_name", ""),
            "avatar_base64": u.get("avatar_base64", ""),
            "is_online": fid in online_users,
            "bio": u.get("bio", ""),
        })
    return {"friends": result}

@fastapi_app.get("/api/friends/requests")
async def list_friend_requests(user: dict = Depends(get_current_user)):
    incoming = await db.friendships.find({"friend_id": user["user_id"], "status": "pending"}, {"_id": 0}).to_list(100)
    outgoing = await db.friendships.find({"user_id": user["user_id"], "status": "pending"}, {"_id": 0}).to_list(100)
    user_ids = [f["user_id"] for f in incoming] + [f["friend_id"] for f in outgoing]
    users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}).to_list(200) if user_ids else []
    user_map = {u["user_id"]: u for u in users}
    incoming_result = [{"friendship_id": f["friendship_id"], "from_user": user_map.get(f["user_id"], {}), "created_at": f["created_at"]} for f in incoming]
    outgoing_result = [{"friendship_id": f["friendship_id"], "to_user": user_map.get(f["friend_id"], {}), "created_at": f["created_at"]} for f in outgoing]
    return {"incoming": incoming_result, "outgoing": outgoing_result}

# ============ SERVER ROUTES ============
@fastapi_app.post("/api/servers")
async def create_server(req: ServerCreate, user: dict = Depends(get_current_user)):
    server_id = f"srv_{uuid.uuid4().hex[:12]}"
    invite_code = secrets.token_urlsafe(8)
    server_doc = {
        "server_id": server_id, "name": sanitize_input(req.name),
        "description": sanitize_input(req.description),
        "icon_letter": req.icon_letter or req.name[0].upper(),
        "icon_base64": "", "banner_base64": "",
        "owner_id": user["user_id"], "invite_code": invite_code,
        "member_count": 1, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.servers.insert_one(server_doc)
    # Create default roles
    everyone_role_id = f"role_{uuid.uuid4().hex[:12]}"
    admin_role_id = f"role_{uuid.uuid4().hex[:12]}"
    await db.roles.insert_many([
        {"role_id": everyone_role_id, "server_id": server_id, "name": "@everyone", "color": "#99AAB5", "permissions": DEFAULT_PERMISSIONS, "position": 0, "is_default": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"role_id": admin_role_id, "server_id": server_id, "name": "Admin", "color": "#E74C3C", "permissions": ADMIN_PERMISSIONS, "position": 1, "is_default": False, "created_at": datetime.now(timezone.utc).isoformat()},
    ])
    await db.server_members.insert_one({
        "server_id": server_id, "user_id": user["user_id"],
        "role": "admin", "role_ids": [admin_role_id, everyone_role_id],
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    channel_id = f"ch_{uuid.uuid4().hex[:12]}"
    await db.channels.insert_one({
        "channel_id": channel_id, "server_id": server_id,
        "name": "general", "channel_type": "text",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    voice_id = f"ch_{uuid.uuid4().hex[:12]}"
    await db.channels.insert_one({
        "channel_id": voice_id, "server_id": server_id,
        "name": "General Voice", "channel_type": "voice",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    server_doc.pop("_id", None)
    return {"server": server_doc, "default_channel_id": channel_id}

@fastapi_app.get("/api/servers")
async def list_servers(user: dict = Depends(get_current_user)):
    memberships = await db.server_members.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    server_ids = [m["server_id"] for m in memberships]
    if not server_ids:
        return {"servers": []}
    servers = await db.servers.find({"server_id": {"$in": server_ids}}, {"_id": 0}).to_list(100)
    role_map = {m["server_id"]: m["role"] for m in memberships}
    for s in servers:
        s["my_role"] = role_map.get(s["server_id"], "member")
    return {"servers": servers}

@fastapi_app.get("/api/servers/{server_id}")
async def get_server(server_id: str, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    membership = await db.server_members.find_one({"server_id": server_id, "user_id": user["user_id"]}, {"_id": 0})
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member")
    server["my_role"] = membership["role"]
    return {"server": server}

@fastapi_app.post("/api/servers/join")
async def join_server(req: JoinServerRequest, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"invite_code": req.invite_code}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if await db.server_members.find_one({"server_id": server["server_id"], "user_id": user["user_id"]}):
        raise HTTPException(status_code=400, detail="Already a member")
    # Get @everyone role
    everyone_role = await db.roles.find_one({"server_id": server["server_id"], "is_default": True}, {"_id": 0})
    role_ids = [everyone_role["role_id"]] if everyone_role else []
    await db.server_members.insert_one({
        "server_id": server["server_id"], "user_id": user["user_id"],
        "role": "member", "role_ids": role_ids,
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.servers.update_one({"server_id": server["server_id"]}, {"$inc": {"member_count": 1}})
    return {"server": server, "message": "Joined successfully"}

@fastapi_app.get("/api/servers/{server_id}/invite")
async def get_invite(server_id: str, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"invite_code": server["invite_code"]}

@fastapi_app.get("/api/servers/{server_id}/members")
async def list_members(server_id: str, user: dict = Depends(get_current_user)):
    memberships = await db.server_members.find({"server_id": server_id}, {"_id": 0}).to_list(200)
    user_ids = [m["user_id"] for m in memberships]
    users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}).to_list(200)
    user_map = {u["user_id"]: u for u in users}
    members = []
    for m in memberships:
        u = user_map.get(m["user_id"], {})
        members.append({
            "user_id": m["user_id"], "username": u.get("username", "Unknown"),
            "display_name": u.get("display_name", ""),
            "avatar_base64": u.get("avatar_base64", ""),
            "role": m["role"], "role_ids": m.get("role_ids", []),
            "is_online": m["user_id"] in online_users,
            "joined_at": m.get("joined_at", ""),
        })
    return {"members": members}

# ============ ROLE ROUTES ============
@fastapi_app.post("/api/servers/{server_id}/roles")
async def create_role(server_id: str, req: RoleCreate, user: dict = Depends(get_current_user)):
    perms = await get_user_server_permissions(user["user_id"], server_id)
    if not has_permission(perms, "manage_roles"):
        raise HTTPException(status_code=403, detail="Missing manage_roles permission")
    role_id = f"role_{uuid.uuid4().hex[:12]}"
    role_doc = {
        "role_id": role_id, "server_id": server_id,
        "name": sanitize_input(req.name), "color": req.color,
        "permissions": req.permissions, "position": req.position,
        "is_default": False, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.roles.insert_one(role_doc)
    role_doc.pop("_id", None)
    return {"role": role_doc}

@fastapi_app.get("/api/servers/{server_id}/roles")
async def list_roles(server_id: str, user: dict = Depends(get_current_user)):
    roles = await db.roles.find({"server_id": server_id}, {"_id": 0}).sort("position", -1).to_list(50)
    return {"roles": roles}

@fastapi_app.put("/api/servers/{server_id}/roles/{role_id}")
async def update_role(server_id: str, role_id: str, req: RoleUpdate, user: dict = Depends(get_current_user)):
    perms = await get_user_server_permissions(user["user_id"], server_id)
    if not has_permission(perms, "manage_roles"):
        raise HTTPException(status_code=403, detail="Missing manage_roles permission")
    update = {}
    if req.name is not None: update["name"] = sanitize_input(req.name)
    if req.color is not None: update["color"] = req.color
    if req.permissions is not None: update["permissions"] = req.permissions
    if req.position is not None: update["position"] = req.position
    if update:
        await db.roles.update_one({"role_id": role_id, "server_id": server_id}, {"$set": update})
    role = await db.roles.find_one({"role_id": role_id}, {"_id": 0})
    return {"role": role}

@fastapi_app.delete("/api/servers/{server_id}/roles/{role_id}")
async def delete_role(server_id: str, role_id: str, user: dict = Depends(get_current_user)):
    perms = await get_user_server_permissions(user["user_id"], server_id)
    if not has_permission(perms, "manage_roles"):
        raise HTTPException(status_code=403, detail="Missing manage_roles permission")
    role = await db.roles.find_one({"role_id": role_id}, {"_id": 0})
    if role and role.get("is_default"):
        raise HTTPException(status_code=400, detail="Cannot delete default role")
    await db.roles.delete_one({"role_id": role_id, "server_id": server_id})
    await db.server_members.update_many({"server_id": server_id}, {"$pull": {"role_ids": role_id}})
    return {"status": "deleted"}

@fastapi_app.put("/api/servers/{server_id}/members/{member_id}/roles")
async def assign_member_roles(server_id: str, member_id: str, request: Request, user: dict = Depends(get_current_user)):
    perms = await get_user_server_permissions(user["user_id"], server_id)
    if not has_permission(perms, "manage_roles"):
        raise HTTPException(status_code=403, detail="Missing manage_roles permission")
    body = await request.json()
    role_ids = body.get("role_ids", [])
    await db.server_members.update_one(
        {"server_id": server_id, "user_id": member_id},
        {"$set": {"role_ids": role_ids}}
    )
    return {"status": "updated"}

# ============ CHANNEL ROUTES ============
@fastapi_app.post("/api/servers/{server_id}/channels")
async def create_channel(server_id: str, req: ChannelCreate, user: dict = Depends(get_current_user)):
    perms = await get_user_server_permissions(user["user_id"], server_id)
    if not has_permission(perms, "manage_channels"):
        raise HTTPException(status_code=403, detail="Missing manage_channels permission")
    channel_id = f"ch_{uuid.uuid4().hex[:12]}"
    channel_doc = {
        "channel_id": channel_id, "server_id": server_id,
        "name": sanitize_input(req.name.lower().replace(" ", "-")),
        "channel_type": req.channel_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.channels.insert_one(channel_doc)
    channel_doc.pop("_id", None)
    return {"channel": channel_doc}

@fastapi_app.get("/api/servers/{server_id}/channels")
async def list_channels(server_id: str, user: dict = Depends(get_current_user)):
    membership = await db.server_members.find_one({"server_id": server_id, "user_id": user["user_id"]})
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member")
    channels = await db.channels.find({"server_id": server_id}, {"_id": 0}).to_list(100)
    # Add voice participant count
    for ch in channels:
        if ch["channel_type"] == "voice":
            participants = await db.voice_participants.count_documents({"channel_id": ch["channel_id"]})
            ch["voice_participant_count"] = participants
    return {"channels": channels}

@fastapi_app.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: str, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    perms = await get_user_server_permissions(user["user_id"], channel["server_id"])
    if not has_permission(perms, "manage_channels"):
        raise HTTPException(status_code=403, detail="Missing manage_channels permission")
    await db.channels.delete_one({"channel_id": channel_id})
    await db.messages.delete_many({"channel_id": channel_id})
    return {"message": "Channel deleted"}

# ============ MESSAGE ROUTES ============
@fastapi_app.get("/api/channels/{channel_id}/messages")
async def get_messages(channel_id: str, limit: int = 50, before: str = None, user: dict = Depends(get_current_user)):
    query = {"channel_id": channel_id}
    if before:
        query["created_at"] = {"$lt": before}
    messages = await db.messages.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()
    sender_ids = list(set(m["sender_id"] for m in messages))
    if sender_ids:
        senders = await db.users.find({"user_id": {"$in": sender_ids}}, {"_id": 0, "password_hash": 0}).to_list(200)
        sender_map = {s["user_id"]: s for s in senders}
        for m in messages:
            s = sender_map.get(m["sender_id"], {})
            m["sender_username"] = s.get("username", "Unknown")
            m["sender_avatar"] = s.get("avatar_base64", "")
            m["sender_display_name"] = s.get("display_name", "")
    return {"messages": messages}

@fastapi_app.post("/api/channels/{channel_id}/messages")
async def send_message(channel_id: str, req: MessageCreate, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    content = sanitize_input(req.content)
    if len(content) > MAX_MSG_LEN:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MAX_MSG_LEN})")
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    msg_doc = {
        "message_id": message_id, "channel_id": channel_id,
        "server_id": channel.get("server_id", ""),
        "sender_id": user["user_id"], "sender_username": user["username"],
        "sender_avatar": user.get("avatar_base64", ""),
        "sender_display_name": user.get("display_name", ""),
        "content": content, "message_type": req.message_type,
        "media_url": req.media_url, "media_type": req.media_type,
        "reactions": [], "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.messages.insert_one(msg_doc)
    msg_doc.pop("_id", None)
    await sio.emit('new_message', msg_doc, room=f"channel_{channel_id}")
    # Push notification to channel members
    await send_channel_notification(channel_id, user["username"], content, user["user_id"])
    return {"message": msg_doc}

@fastapi_app.post("/api/messages/{message_id}/react")
async def add_reaction(message_id: str, req: ReactionRequest, user: dict = Depends(get_current_user)):
    msg = await db.messages.find_one({"message_id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    reactions = msg.get("reactions", [])
    existing = next((r for r in reactions if r["emoji"] == req.emoji), None)
    if existing:
        if user["user_id"] not in existing["users"]:
            existing["users"].append(user["user_id"])
            existing["count"] += 1
    else:
        reactions.append({"emoji": req.emoji, "users": [user["user_id"]], "count": 1})
    await db.messages.update_one({"message_id": message_id}, {"$set": {"reactions": reactions}})
    await sio.emit('reaction_update', {"message_id": message_id, "reactions": reactions}, room=f"channel_{msg.get('channel_id', '')}")
    return {"reactions": reactions}

@fastapi_app.delete("/api/messages/{message_id}/react/{emoji}")
async def remove_reaction(message_id: str, emoji: str, user: dict = Depends(get_current_user)):
    msg = await db.messages.find_one({"message_id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    reactions = msg.get("reactions", [])
    for r in reactions:
        if r["emoji"] == emoji and user["user_id"] in r["users"]:
            r["users"].remove(user["user_id"])
            r["count"] -= 1
            if r["count"] <= 0:
                reactions.remove(r)
            break
    await db.messages.update_one({"message_id": message_id}, {"$set": {"reactions": reactions}})
    await sio.emit('reaction_update', {"message_id": message_id, "reactions": reactions}, room=f"channel_{msg.get('channel_id', '')}")
    return {"reactions": reactions}

@fastapi_app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str, user: dict = Depends(get_current_user)):
    msg = await db.messages.find_one({"message_id": message_id}, {"_id": 0})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg["sender_id"] != user["user_id"]:
        perms = await get_user_server_permissions(user["user_id"], msg.get("server_id", ""))
        if not has_permission(perms, "manage_messages"):
            raise HTTPException(status_code=403, detail="Cannot delete this message")
    await db.messages.delete_one({"message_id": message_id})
    await sio.emit('message_deleted', {"message_id": message_id}, room=f"channel_{msg['channel_id']}")
    return {"status": "deleted"}

# ============ DM ROUTES WITH E2EE SUPPORT ============
@fastapi_app.post("/api/dms")
async def create_dm(req: DMCreate, user: dict = Depends(get_current_user)):
    recipient = await db.users.find_one({"user_id": req.recipient_id}, {"_id": 0, "password_hash": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    participants = sorted([user["user_id"], req.recipient_id])
    existing = await db.dms.find_one({"participants": participants}, {"_id": 0})
    if existing:
        return {"dm": existing}
    dm_id = f"dm_{uuid.uuid4().hex[:12]}"
    dm_doc = {
        "dm_id": dm_id, "participants": participants,
        "encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_message": None, "last_message_at": None,
    }
    await db.dms.insert_one(dm_doc)
    dm_doc.pop("_id", None)
    return {"dm": dm_doc}

@fastapi_app.get("/api/dms")
async def list_dms(user: dict = Depends(get_current_user)):
    dms = await db.dms.find({"participants": user["user_id"]}, {"_id": 0}).sort("last_message_at", -1).to_list(100)
    for dm_item in dms:
        other_id = [p for p in dm_item["participants"] if p != user["user_id"]]
        if other_id:
            other_user = await db.users.find_one({"user_id": other_id[0]}, {"_id": 0, "password_hash": 0})
            if other_user:
                dm_item["other_user"] = {
                    "user_id": other_user["user_id"], "username": other_user["username"],
                    "display_name": other_user.get("display_name", ""),
                    "avatar_base64": other_user.get("avatar_base64", ""),
                    "is_online": other_user["user_id"] in online_users,
                }
    return {"dms": dms}

@fastapi_app.get("/api/dms/{dm_id}/messages")
async def get_dm_messages(dm_id: str, limit: int = 50, before: str = None, user: dict = Depends(get_current_user)):
    dm_conv = await db.dms.find_one({"dm_id": dm_id}, {"_id": 0})
    if not dm_conv or user["user_id"] not in dm_conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    query = {"dm_id": dm_id}
    if before:
        query["created_at"] = {"$lt": before}
    messages = await db.dm_messages.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()
    return {"messages": messages}

@fastapi_app.post("/api/dms/{dm_id}/messages")
async def send_dm_message(dm_id: str, req: MessageCreate, user: dict = Depends(get_current_user)):
    dm_conv = await db.dms.find_one({"dm_id": dm_id}, {"_id": 0})
    if not dm_conv or user["user_id"] not in dm_conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    content = sanitize_input(req.content)
    if len(content) > MAX_MSG_LEN:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MAX_MSG_LEN})")
    message_id = f"dmsg_{uuid.uuid4().hex[:12]}"
    msg_doc = {
        "message_id": message_id, "dm_id": dm_id,
        "sender_id": user["user_id"], "sender_username": user["username"],
        "sender_avatar": user.get("avatar_base64", ""),
        "content": content, "message_type": req.message_type,
        "media_url": req.media_url, "media_type": req.media_type,
        "encrypted": dm_conv.get("encrypted", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dm_messages.insert_one(msg_doc)
    msg_doc.pop("_id", None)
    await db.dms.update_one({"dm_id": dm_id}, {"$set": {"last_message": content[:100], "last_message_at": datetime.now(timezone.utc).isoformat()}})
    await sio.emit('new_dm_message', msg_doc, room=f"dm_{dm_id}")
    # Push notification
    other_id = [p for p in dm_conv["participants"] if p != user["user_id"]]
    if other_id:
        await send_push_to_user(other_id[0], f"Message from {user['username']}", content[:100])
    return {"message": msg_doc}

# E2E Key Exchange
@fastapi_app.post("/api/dms/{dm_id}/keys")
async def exchange_e2e_key(dm_id: str, req: E2EKeyExchange, user: dict = Depends(get_current_user)):
    dm_conv = await db.dms.find_one({"dm_id": dm_id}, {"_id": 0})
    if not dm_conv or user["user_id"] not in dm_conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    await db.e2e_keys.update_one(
        {"dm_id": dm_id, "user_id": user["user_id"]},
        {"$set": {"dm_id": dm_id, "user_id": user["user_id"], "public_key": req.public_key, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"status": "key_stored"}

@fastapi_app.get("/api/dms/{dm_id}/keys")
async def get_e2e_keys(dm_id: str, user: dict = Depends(get_current_user)):
    dm_conv = await db.dms.find_one({"dm_id": dm_id}, {"_id": 0})
    if not dm_conv or user["user_id"] not in dm_conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    keys = await db.e2e_keys.find({"dm_id": dm_id}, {"_id": 0}).to_list(2)
    return {"keys": keys}

# ============ USER ROUTES ============
@fastapi_app.get("/api/users/search")
async def search_users(q: str = "", user: dict = Depends(get_current_user)):
    if not q or len(q) < 2:
        return {"users": []}
    users = await db.users.find(
        {"username": {"$regex": re.escape(q), "$options": "i"}, "user_id": {"$ne": user["user_id"]}},
        {"_id": 0, "password_hash": 0}
    ).limit(20).to_list(20)
    for u in users:
        u["is_online"] = u["user_id"] in online_users
    return {"users": users}

@fastapi_app.get("/api/users/{user_id}")
async def get_user_profile(user_id: str, user: dict = Depends(get_current_user)):
    profile = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    profile["is_online"] = user_id in online_users
    # Check friendship
    friendship = await db.friendships.find_one({
        "$or": [
            {"user_id": user["user_id"], "friend_id": user_id},
            {"user_id": user_id, "friend_id": user["user_id"]},
        ]
    }, {"_id": 0})
    profile["friendship_status"] = friendship.get("status") if friendship else None
    profile["friendship_id"] = friendship.get("friendship_id") if friendship else None
    return {"user": profile}

@fastapi_app.put("/api/users/me")
async def update_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    update_fields = {}
    if req.username is not None:
        username = sanitize_input(req.username.strip())
        if not re.match(r'^[a-zA-Z0-9_.]{2,32}$', username):
            raise HTTPException(status_code=400, detail="Invalid username format")
        if await db.users.find_one({"username": username, "user_id": {"$ne": user["user_id"]}}):
            raise HTTPException(status_code=400, detail="Username already taken")
        update_fields["username"] = username
    if req.bio is not None:
        update_fields["bio"] = sanitize_input(req.bio)[:500]
    if req.avatar_base64 is not None:
        update_fields["avatar_base64"] = req.avatar_base64
    if req.banner_base64 is not None:
        update_fields["banner_base64"] = req.banner_base64
    if req.status is not None:
        update_fields["status"] = req.status
    if req.display_name is not None:
        update_fields["display_name"] = sanitize_input(req.display_name)[:50]
    if update_fields:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": update_fields})
    updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": updated}

# ============ MEDIA UPLOAD ============
@fastapi_app.post("/api/upload")
async def upload_media(req: UploadRequest, user: dict = Depends(get_current_user)):
    max_size = CONFIG.get("security", {}).get("max_upload_size_mb", 10) * 1024 * 1024
    try:
        data_bytes = base64.b64decode(req.data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")
    if len(data_bytes) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large (max {max_size // (1024*1024)}MB)")
    # Store in MongoDB (Supabase can be used when configured)
    file_id = f"file_{uuid.uuid4().hex[:12]}"
    await db.uploads.insert_one({
        "file_id": file_id, "user_id": user["user_id"],
        "filename": sanitize_input(req.filename),
        "content_type": req.content_type,
        "data": req.data,
        "size": len(data_bytes),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"file_id": file_id, "url": f"/api/files/{file_id}"}

@fastapi_app.get("/api/files/{file_id}")
async def get_file(file_id: str):
    file_doc = await db.uploads.find_one({"file_id": file_id}, {"_id": 0})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    from starlette.responses import Response
    data_bytes = base64.b64decode(file_doc["data"])
    return Response(content=data_bytes, media_type=file_doc.get("content_type", "application/octet-stream"))

# ============ STICKER/GIF ============
BUILT_IN_STICKERS = [
    {"pack": "reactions", "stickers": [
        {"id": "s1", "emoji": "😂", "name": "laugh"},
        {"id": "s2", "emoji": "❤️", "name": "love"},
        {"id": "s3", "emoji": "🔥", "name": "fire"},
        {"id": "s4", "emoji": "👀", "name": "eyes"},
        {"id": "s5", "emoji": "💀", "name": "skull"},
        {"id": "s6", "emoji": "🎉", "name": "party"},
        {"id": "s7", "emoji": "😎", "name": "cool"},
        {"id": "s8", "emoji": "🤔", "name": "think"},
        {"id": "s9", "emoji": "👍", "name": "thumbsup"},
        {"id": "s10", "emoji": "😢", "name": "sad"},
        {"id": "s11", "emoji": "😡", "name": "angry"},
        {"id": "s12", "emoji": "🥺", "name": "pleading"},
    ]},
    {"pack": "animals", "stickers": [
        {"id": "a1", "emoji": "🐱", "name": "cat"},
        {"id": "a2", "emoji": "🐶", "name": "dog"},
        {"id": "a3", "emoji": "🦊", "name": "fox"},
        {"id": "a4", "emoji": "🐸", "name": "frog"},
        {"id": "a5", "emoji": "🐧", "name": "penguin"},
        {"id": "a6", "emoji": "🦉", "name": "owl"},
        {"id": "a7", "emoji": "🐼", "name": "panda"},
        {"id": "a8", "emoji": "🦋", "name": "butterfly"},
    ]},
    {"pack": "gestures", "stickers": [
        {"id": "g1", "emoji": "👋", "name": "wave"},
        {"id": "g2", "emoji": "🤝", "name": "handshake"},
        {"id": "g3", "emoji": "✌️", "name": "peace"},
        {"id": "g4", "emoji": "🫡", "name": "salute"},
        {"id": "g5", "emoji": "💪", "name": "flex"},
        {"id": "g6", "emoji": "🙏", "name": "pray"},
    ]},
]

@fastapi_app.get("/api/stickers")
async def get_stickers():
    return {"sticker_packs": BUILT_IN_STICKERS}

@fastapi_app.get("/api/gifs/search")
async def search_gifs(q: str = "", limit: int = 20):
    tenor_key = CONFIG.get("gif_providers", {}).get("tenor_api_key", "")
    giphy_key = CONFIG.get("gif_providers", {}).get("giphy_api_key", "")
    results = []
    if tenor_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://tenor.googleapis.com/v2/search?q={q}&key={tenor_key}&limit={limit}")
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        media = r.get("media_formats", {}).get("tinygif", {})
                        results.append({"id": r["id"], "url": media.get("url", ""), "preview": media.get("url", ""), "source": "tenor"})
        except Exception:
            pass
    if giphy_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.giphy.com/v1/gifs/search?api_key={giphy_key}&q={q}&limit={limit}")
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("data", []):
                        results.append({"id": r["id"], "url": r["images"]["fixed_height"]["url"], "preview": r["images"]["fixed_height_small"]["url"], "source": "giphy"})
        except Exception:
            pass
    return {"gifs": results, "has_api_keys": bool(tenor_key or giphy_key)}

# ============ PUSH NOTIFICATIONS ============
@fastapi_app.post("/api/push/register")
async def register_push_token(req: PushTokenRegister, user: dict = Depends(get_current_user)):
    await db.push_tokens.update_one(
        {"user_id": user["user_id"], "push_token": req.push_token},
        {"$set": {"user_id": user["user_id"], "push_token": req.push_token, "device_type": req.device_type, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"status": "registered"}

async def send_push_to_user(user_id: str, title: str, body: str):
    tokens = await db.push_tokens.find({"user_id": user_id}, {"_id": 0}).to_list(10)
    if not tokens:
        return
    expo_tokens = [t["push_token"] for t in tokens if t["push_token"].startswith("ExponentPushToken")]
    if not expo_tokens:
        return
    messages = [{"to": token, "title": title, "body": body, "sound": "default"} for token in expo_tokens]
    try:
        async with httpx.AsyncClient() as client:
            await client.post("https://exp.host/--/api/v2/push/send", json=messages, headers={"Content-Type": "application/json"})
    except Exception as e:
        logger.error(f"Push notification error: {e}")

async def send_channel_notification(channel_id: str, sender_name: str, content: str, sender_id: str):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel:
        return
    members = await db.server_members.find({"server_id": channel.get("server_id", "")}, {"_id": 0}).to_list(200)
    for m in members:
        if m["user_id"] != sender_id and m["user_id"] not in online_users:
            await send_push_to_user(m["user_id"], f"#{channel['name']} - {sender_name}", content[:100])

# ============ SEARCH ============
@fastapi_app.get("/api/search")
async def search(q: str = "", user: dict = Depends(get_current_user)):
    if not q or len(q) < 2:
        return {"servers": [], "users": [], "messages": []}
    escaped_q = re.escape(q)
    servers = await db.servers.find({"name": {"$regex": escaped_q, "$options": "i"}}, {"_id": 0}).limit(10).to_list(10)
    users = await db.users.find(
        {"username": {"$regex": escaped_q, "$options": "i"}},
        {"_id": 0, "password_hash": 0}
    ).limit(10).to_list(10)
    memberships = await db.server_members.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    server_ids = [m["server_id"] for m in memberships]
    messages = []
    if server_ids:
        messages = await db.messages.find(
            {"server_id": {"$in": server_ids}, "content": {"$regex": escaped_q, "$options": "i"}},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
    return {"servers": servers, "users": users, "messages": messages}

# ============ VOICE CHANNEL (WebRTC Signaling) ============
@fastapi_app.post("/api/channels/{channel_id}/voice/join")
async def join_voice_channel(channel_id: str, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel or channel.get("channel_type") != "voice":
        raise HTTPException(status_code=400, detail="Not a voice channel")
    await db.voice_participants.update_one(
        {"channel_id": channel_id, "user_id": user["user_id"]},
        {"$set": {"channel_id": channel_id, "user_id": user["user_id"], "username": user["username"], "muted": False, "deafened": False, "joined_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    participants = await db.voice_participants.find({"channel_id": channel_id}, {"_id": 0}).to_list(50)
    await sio.emit('voice_update', {"channel_id": channel_id, "participants": participants}, room=f"voice_{channel_id}")
    return {"participants": participants}

@fastapi_app.post("/api/channels/{channel_id}/voice/leave")
async def leave_voice_channel(channel_id: str, user: dict = Depends(get_current_user)):
    await db.voice_participants.delete_one({"channel_id": channel_id, "user_id": user["user_id"]})
    participants = await db.voice_participants.find({"channel_id": channel_id}, {"_id": 0}).to_list(50)
    await sio.emit('voice_update', {"channel_id": channel_id, "participants": participants}, room=f"voice_{channel_id}")
    return {"participants": participants}

@fastapi_app.post("/api/channels/{channel_id}/voice/toggle")
async def toggle_voice_state(channel_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    update = {}
    if "muted" in body:
        update["muted"] = body["muted"]
    if "deafened" in body:
        update["deafened"] = body["deafened"]
    if update:
        await db.voice_participants.update_one({"channel_id": channel_id, "user_id": user["user_id"]}, {"$set": update})
    participants = await db.voice_participants.find({"channel_id": channel_id}, {"_id": 0}).to_list(50)
    await sio.emit('voice_update', {"channel_id": channel_id, "participants": participants}, room=f"voice_{channel_id}")
    return {"participants": participants}

@fastapi_app.get("/api/channels/{channel_id}/voice/participants")
async def get_voice_participants(channel_id: str, user: dict = Depends(get_current_user)):
    participants = await db.voice_participants.find({"channel_id": channel_id}, {"_id": 0}).to_list(50)
    return {"participants": participants}

# ============ SOCKET.IO EVENTS ============
@sio.event
async def connect(sid, environ, auth):
    token = auth.get("token") if auth and isinstance(auth, dict) else None
    if not token:
        return False
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["sub"]
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return False
        sid_user_map[sid] = user_id
        if user_id not in online_users:
            online_users[user_id] = set()
        online_users[user_id].add(sid)
        await db.users.update_one({"user_id": user_id}, {"$set": {"status": "online"}})
        # Join personal room for notifications
        await sio.enter_room(sid, f"user_{user_id}")
        await sio.emit('user_online', {"user_id": user_id}, skip_sid=sid)
    except Exception as e:
        logger.error(f"Socket auth error: {e}")
        return False

@sio.event
async def disconnect(sid):
    user_id = sid_user_map.pop(sid, None)
    if user_id and user_id in online_users:
        online_users[user_id].discard(sid)
        if not online_users[user_id]:
            del online_users[user_id]
            await db.users.update_one({"user_id": user_id}, {"$set": {"status": "offline"}})
            # Remove from voice channels
            await db.voice_participants.delete_many({"user_id": user_id})
            await sio.emit('user_offline', {"user_id": user_id})

@sio.event
async def join_channel(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if channel_id:
        await sio.enter_room(sid, f"channel_{channel_id}")

@sio.event
async def leave_channel(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if channel_id:
        await sio.leave_room(sid, f"channel_{channel_id}")

@sio.event
async def join_dm(sid, data):
    dm_id = data.get("dm_id") if isinstance(data, dict) else None
    if dm_id:
        await sio.enter_room(sid, f"dm_{dm_id}")

@sio.event
async def leave_dm(sid, data):
    dm_id = data.get("dm_id") if isinstance(data, dict) else None
    if dm_id:
        await sio.leave_room(sid, f"dm_{dm_id}")

@sio.event
async def typing(sid, data):
    if not isinstance(data, dict):
        return
    user_id = sid_user_map.get(sid)
    if not user_id:
        return
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    username = user.get("username", "Someone") if user else "Someone"
    channel_id = data.get("channel_id")
    dm_id = data.get("dm_id")
    if channel_id:
        await sio.emit('user_typing', {"user_id": user_id, "username": username, "channel_id": channel_id}, room=f"channel_{channel_id}", skip_sid=sid)
    elif dm_id:
        await sio.emit('user_typing', {"user_id": user_id, "username": username, "dm_id": dm_id}, room=f"dm_{dm_id}", skip_sid=sid)

# Voice signaling
@sio.event
async def join_voice(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if channel_id:
        await sio.enter_room(sid, f"voice_{channel_id}")
        user_id = sid_user_map.get(sid)
        if user_id:
            await sio.emit('voice_user_joined', {"user_id": user_id, "sid": sid}, room=f"voice_{channel_id}", skip_sid=sid)

@sio.event
async def leave_voice(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if channel_id:
        await sio.leave_room(sid, f"voice_{channel_id}")
        user_id = sid_user_map.get(sid)
        if user_id:
            await sio.emit('voice_user_left', {"user_id": user_id}, room=f"voice_{channel_id}")

@sio.event
async def voice_offer(sid, data):
    target_sid = data.get("target_sid") if isinstance(data, dict) else None
    if target_sid:
        await sio.emit('voice_offer', {"offer": data.get("offer"), "from_sid": sid}, to=target_sid)

@sio.event
async def voice_answer(sid, data):
    target_sid = data.get("target_sid") if isinstance(data, dict) else None
    if target_sid:
        await sio.emit('voice_answer', {"answer": data.get("answer"), "from_sid": sid}, to=target_sid)

@sio.event
async def voice_ice_candidate(sid, data):
    target_sid = data.get("target_sid") if isinstance(data, dict) else None
    if target_sid:
        await sio.emit('voice_ice_candidate', {"candidate": data.get("candidate"), "from_sid": sid}, to=target_sid)

# ============ STARTUP ============
@fastapi_app.on_event("startup")
async def startup():
    logger.info("Starting KarasuWorld API...")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("username")
    await db.servers.create_index("server_id", unique=True)
    await db.servers.create_index("invite_code")
    await db.server_members.create_index([("server_id", 1), ("user_id", 1)], unique=True)
    await db.channels.create_index("channel_id", unique=True)
    await db.channels.create_index("server_id")
    await db.messages.create_index("channel_id")
    await db.messages.create_index("message_id", unique=True)
    await db.dms.create_index("dm_id", unique=True)
    await db.dms.create_index("participants")
    await db.dm_messages.create_index("dm_id")
    await db.voice_participants.create_index([("channel_id", 1), ("user_id", 1)], unique=True)
    await db.friendships.create_index("friendship_id", unique=True)
    await db.friendships.create_index([("user_id", 1), ("friend_id", 1)])
    await db.roles.create_index("role_id", unique=True)
    await db.roles.create_index("server_id")
    await db.push_tokens.create_index([("user_id", 1), ("push_token", 1)], unique=True)
    await db.e2e_keys.create_index([("dm_id", 1), ("user_id", 1)], unique=True)
    await db.uploads.create_index("file_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@karasuworld.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "KarasuAdmin123!")
    if not await db.users.find_one({"email": admin_email}):
        admin_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": admin_id, "email": admin_email,
            "username": "KarasuAdmin", "display_name": "KarasuAdmin",
            "password_hash": hash_password(admin_password),
            "bio": "System Administrator", "avatar_base64": "", "banner_base64": "",
            "status": "offline", "custom_status": "", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin seeded: {admin_email}")
    os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"# KarasuWorld Test Credentials\n\n## Admin\n- Email: {admin_email}\n- Password: {admin_password}\n\n## Test User\n- Email: testuser@test.com\n- Password: Test123!!\n")
    logger.info("KarasuWorld API started successfully")

@fastapi_app.on_event("shutdown")
async def shutdown():
    db_client.close()

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/api/socket.io')
