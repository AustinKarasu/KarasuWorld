from dotenv import load_dotenv
load_dotenv()

import socketio
from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import bcrypt
import jwt
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB
mongo_url = os.environ['MONGO_URL']
db_client = AsyncIOMotorClient(mongo_url)
db = db_client[os.environ.get('DB_NAME', 'karasuworld')]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = "HS256"

# Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', logger=False, engineio_logger=False)
fastapi_app = FastAPI(title="KarasuWorld API")

# Track online users: {user_id: set(sid)}
online_users = {}
# Track sid -> user_id mapping
sid_user_map = {}

# ============ MODELS ============

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ServerCreate(BaseModel):
    name: str
    description: str = ""
    icon_letter: str = ""

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "text"

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"

class DMCreate(BaseModel):
    recipient_id: str

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None

class ReactionRequest(BaseModel):
    emoji: str

class JoinServerRequest(BaseModel):
    invite_code: str

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
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
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

def serialize_user(user: dict) -> dict:
    u = {k: v for k, v in user.items() if k != '_id' and k != 'password_hash'}
    u['is_online'] = u.get('user_id', '') in online_users
    return u

# ============ AUTH ROUTES ============

@fastapi_app.post("/api/auth/register")
async def register(req: RegisterRequest):
    email = req.email.lower().strip()
    if await db.users.find_one({"email": email}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": req.username}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": email,
        "username": req.username,
        "password_hash": hash_password(req.password),
        "bio": "",
        "avatar_url": "",
        "status": "online",
        "role": "member",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    user_doc.pop("password_hash")
    user_doc.pop("_id", None)
    return {"user": user_doc, "access_token": access_token, "refresh_token": refresh_token}

@fastapi_app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_id = user["user_id"]
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    user_data = {k: v for k, v in user.items() if k != '_id' and k != 'password_hash'}
    return {"user": user_data, "access_token": access_token, "refresh_token": refresh_token}

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
        new_access = create_access_token(payload["sub"], user["email"])
        return {"access_token": new_access}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ============ SERVER ROUTES ============

@fastapi_app.post("/api/servers")
async def create_server(req: ServerCreate, user: dict = Depends(get_current_user)):
    server_id = f"srv_{uuid.uuid4().hex[:12]}"
    invite_code = secrets.token_urlsafe(8)
    icon_letter = req.icon_letter or req.name[0].upper()
    server_doc = {
        "server_id": server_id,
        "name": req.name,
        "description": req.description,
        "icon_letter": icon_letter,
        "owner_id": user["user_id"],
        "invite_code": invite_code,
        "member_count": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.servers.insert_one(server_doc)
    # Add owner as admin member
    await db.server_members.insert_one({
        "server_id": server_id,
        "user_id": user["user_id"],
        "role": "admin",
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    # Create default general channel
    channel_id = f"ch_{uuid.uuid4().hex[:12]}"
    await db.channels.insert_one({
        "channel_id": channel_id,
        "server_id": server_id,
        "name": "general",
        "channel_type": "text",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    server_doc.pop("_id", None)
    return {"server": server_doc, "default_channel_id": channel_id}

@fastapi_app.get("/api/servers")
async def list_servers(user: dict = Depends(get_current_user)):
    memberships = await db.server_members.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).to_list(100)
    server_ids = [m["server_id"] for m in memberships]
    if not server_ids:
        return {"servers": []}
    servers = await db.servers.find(
        {"server_id": {"$in": server_ids}}, {"_id": 0}
    ).to_list(100)
    # Add user's role in each server
    role_map = {m["server_id"]: m["role"] for m in memberships}
    for s in servers:
        s["my_role"] = role_map.get(s["server_id"], "member")
    return {"servers": servers}

@fastapi_app.get("/api/servers/{server_id}")
async def get_server(server_id: str, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    membership = await db.server_members.find_one(
        {"server_id": server_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this server")
    server["my_role"] = membership["role"]
    return {"server": server}

@fastapi_app.post("/api/servers/join")
async def join_server(req: JoinServerRequest, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"invite_code": req.invite_code}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    existing = await db.server_members.find_one(
        {"server_id": server["server_id"], "user_id": user["user_id"]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    await db.server_members.insert_one({
        "server_id": server["server_id"],
        "user_id": user["user_id"],
        "role": "member",
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.servers.update_one(
        {"server_id": server["server_id"]},
        {"$inc": {"member_count": 1}}
    )
    return {"server": server, "message": "Joined successfully"}

@fastapi_app.get("/api/servers/{server_id}/invite")
async def get_invite(server_id: str, user: dict = Depends(get_current_user)):
    server = await db.servers.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"invite_code": server["invite_code"]}

@fastapi_app.get("/api/servers/{server_id}/members")
async def list_members(server_id: str, user: dict = Depends(get_current_user)):
    memberships = await db.server_members.find(
        {"server_id": server_id}, {"_id": 0}
    ).to_list(200)
    user_ids = [m["user_id"] for m in memberships]
    users = await db.users.find(
        {"user_id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(200)
    user_map = {u["user_id"]: u for u in users}
    members = []
    for m in memberships:
        u = user_map.get(m["user_id"], {})
        members.append({
            "user_id": m["user_id"],
            "username": u.get("username", "Unknown"),
            "avatar_url": u.get("avatar_url", ""),
            "role": m["role"],
            "is_online": m["user_id"] in online_users,
            "joined_at": m.get("joined_at", ""),
        })
    return {"members": members}

@fastapi_app.put("/api/servers/{server_id}/members/{member_id}/role")
async def update_member_role(server_id: str, member_id: str, role: str, user: dict = Depends(get_current_user)):
    membership = await db.server_members.find_one(
        {"server_id": server_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not membership or membership["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles")
    if role not in ["admin", "moderator", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.server_members.update_one(
        {"server_id": server_id, "user_id": member_id},
        {"$set": {"role": role}}
    )
    return {"message": "Role updated"}

# ============ CHANNEL ROUTES ============

@fastapi_app.post("/api/servers/{server_id}/channels")
async def create_channel(server_id: str, req: ChannelCreate, user: dict = Depends(get_current_user)):
    membership = await db.server_members.find_one(
        {"server_id": server_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not membership or membership["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    channel_id = f"ch_{uuid.uuid4().hex[:12]}"
    channel_doc = {
        "channel_id": channel_id,
        "server_id": server_id,
        "name": req.name.lower().replace(" ", "-"),
        "channel_type": req.channel_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.channels.insert_one(channel_doc)
    channel_doc.pop("_id", None)
    return {"channel": channel_doc}

@fastapi_app.get("/api/servers/{server_id}/channels")
async def list_channels(server_id: str, user: dict = Depends(get_current_user)):
    membership = await db.server_members.find_one(
        {"server_id": server_id, "user_id": user["user_id"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member")
    channels = await db.channels.find(
        {"server_id": server_id}, {"_id": 0}
    ).to_list(100)
    return {"channels": channels}

@fastapi_app.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: str, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    membership = await db.server_members.find_one(
        {"server_id": channel["server_id"], "user_id": user["user_id"]}, {"_id": 0}
    )
    if not membership or membership["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete channels")
    await db.channels.delete_one({"channel_id": channel_id})
    await db.messages.delete_many({"channel_id": channel_id})
    return {"message": "Channel deleted"}

# ============ MESSAGE ROUTES ============

@fastapi_app.get("/api/channels/{channel_id}/messages")
async def get_messages(channel_id: str, limit: int = 50, before: str = None, user: dict = Depends(get_current_user)):
    query = {"channel_id": channel_id}
    if before:
        query["created_at"] = {"$lt": before}
    messages = await db.messages.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()
    # Attach sender info
    sender_ids = list(set(m["sender_id"] for m in messages))
    if sender_ids:
        senders = await db.users.find(
            {"user_id": {"$in": sender_ids}}, {"_id": 0, "password_hash": 0}
        ).to_list(200)
        sender_map = {s["user_id"]: s for s in senders}
        for m in messages:
            sender = sender_map.get(m["sender_id"], {})
            m["sender_username"] = sender.get("username", "Unknown")
            m["sender_avatar"] = sender.get("avatar_url", "")
    return {"messages": messages}

@fastapi_app.post("/api/channels/{channel_id}/messages")
async def send_message(channel_id: str, req: MessageCreate, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    msg_doc = {
        "message_id": message_id,
        "channel_id": channel_id,
        "server_id": channel.get("server_id", ""),
        "sender_id": user["user_id"],
        "sender_username": user["username"],
        "sender_avatar": user.get("avatar_url", ""),
        "content": req.content,
        "message_type": req.message_type,
        "reactions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.messages.insert_one(msg_doc)
    msg_doc.pop("_id", None)
    # Broadcast via Socket.IO
    await sio.emit('new_message', msg_doc, room=f"channel_{channel_id}")
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
    await db.messages.update_one(
        {"message_id": message_id},
        {"$set": {"reactions": reactions}}
    )
    channel_id = msg.get("channel_id", "")
    await sio.emit('reaction_update', {
        "message_id": message_id,
        "reactions": reactions
    }, room=f"channel_{channel_id}")
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
    await db.messages.update_one(
        {"message_id": message_id},
        {"$set": {"reactions": reactions}}
    )
    channel_id = msg.get("channel_id", "")
    await sio.emit('reaction_update', {
        "message_id": message_id,
        "reactions": reactions
    }, room=f"channel_{channel_id}")
    return {"reactions": reactions}

# ============ DM ROUTES ============

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
        "dm_id": dm_id,
        "participants": participants,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_message": None,
        "last_message_at": None,
    }
    await db.dms.insert_one(dm_doc)
    dm_doc.pop("_id", None)
    return {"dm": dm_doc}

@fastapi_app.get("/api/dms")
async def list_dms(user: dict = Depends(get_current_user)):
    dms = await db.dms.find(
        {"participants": user["user_id"]}, {"_id": 0}
    ).sort("last_message_at", -1).to_list(100)
    # Attach other user info
    for dm_item in dms:
        other_id = [p for p in dm_item["participants"] if p != user["user_id"]]
        if other_id:
            other_user = await db.users.find_one(
                {"user_id": other_id[0]}, {"_id": 0, "password_hash": 0}
            )
            if other_user:
                dm_item["other_user"] = {
                    "user_id": other_user["user_id"],
                    "username": other_user["username"],
                    "avatar_url": other_user.get("avatar_url", ""),
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
    messages = await db.dm_messages.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()
    return {"messages": messages}

@fastapi_app.post("/api/dms/{dm_id}/messages")
async def send_dm_message(dm_id: str, req: MessageCreate, user: dict = Depends(get_current_user)):
    dm_conv = await db.dms.find_one({"dm_id": dm_id}, {"_id": 0})
    if not dm_conv or user["user_id"] not in dm_conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    message_id = f"dmsg_{uuid.uuid4().hex[:12]}"
    msg_doc = {
        "message_id": message_id,
        "dm_id": dm_id,
        "sender_id": user["user_id"],
        "sender_username": user["username"],
        "sender_avatar": user.get("avatar_url", ""),
        "content": req.content,
        "message_type": req.message_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dm_messages.insert_one(msg_doc)
    msg_doc.pop("_id", None)
    await db.dms.update_one(
        {"dm_id": dm_id},
        {"$set": {"last_message": req.content, "last_message_at": datetime.now(timezone.utc).isoformat()}}
    )
    await sio.emit('new_dm_message', msg_doc, room=f"dm_{dm_id}")
    return {"message": msg_doc}

# ============ USER ROUTES ============

@fastapi_app.get("/api/users/search")
async def search_users(q: str = "", user: dict = Depends(get_current_user)):
    if not q or len(q) < 2:
        return {"users": []}
    users = await db.users.find(
        {"username": {"$regex": q, "$options": "i"}, "user_id": {"$ne": user["user_id"]}},
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
    return {"user": profile}

@fastapi_app.put("/api/users/me")
async def update_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    update_fields = {}
    if req.username is not None:
        existing = await db.users.find_one({"username": req.username, "user_id": {"$ne": user["user_id"]}})
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        update_fields["username"] = req.username
    if req.bio is not None:
        update_fields["bio"] = req.bio
    if req.avatar_url is not None:
        update_fields["avatar_url"] = req.avatar_url
    if req.status is not None:
        update_fields["status"] = req.status
    if update_fields:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": update_fields})
    updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": updated}

# ============ SOCKET.IO EVENTS ============

@sio.event
async def connect(sid, environ, auth):
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        logger.warning(f"Socket connect without token: {sid}")
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
        logger.info(f"Socket connected: {sid} (user: {user_id})")
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
            await sio.emit('user_offline', {"user_id": user_id})
    logger.info(f"Socket disconnected: {sid}")

@sio.event
async def join_channel(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if not channel_id:
        return
    room = f"channel_{channel_id}"
    await sio.enter_room(sid, room)
    logger.info(f"{sid} joined channel room {room}")

@sio.event
async def leave_channel(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    if not channel_id:
        return
    room = f"channel_{channel_id}"
    await sio.leave_room(sid, room)
    logger.info(f"{sid} left channel room {room}")

@sio.event
async def join_dm(sid, data):
    dm_id = data.get("dm_id") if isinstance(data, dict) else None
    if not dm_id:
        return
    room = f"dm_{dm_id}"
    await sio.enter_room(sid, room)
    logger.info(f"{sid} joined DM room {room}")

@sio.event
async def leave_dm(sid, data):
    dm_id = data.get("dm_id") if isinstance(data, dict) else None
    if not dm_id:
        return
    room = f"dm_{dm_id}"
    await sio.leave_room(sid, room)

@sio.event
async def typing(sid, data):
    channel_id = data.get("channel_id") if isinstance(data, dict) else None
    dm_id = data.get("dm_id") if isinstance(data, dict) else None
    user_id = sid_user_map.get(sid)
    if not user_id:
        return
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    username = user.get("username", "Someone") if user else "Someone"
    if channel_id:
        await sio.emit('user_typing', {
            "user_id": user_id,
            "username": username,
            "channel_id": channel_id
        }, room=f"channel_{channel_id}", skip_sid=sid)
    elif dm_id:
        await sio.emit('user_typing', {
            "user_id": user_id,
            "username": username,
            "dm_id": dm_id
        }, room=f"dm_{dm_id}", skip_sid=sid)

# ============ VOICE CHANNEL ROUTES ============

@fastapi_app.post("/api/channels/{channel_id}/voice/join")
async def join_voice_channel(channel_id: str, user: dict = Depends(get_current_user)):
    channel = await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})
    if not channel or channel.get("channel_type") != "voice":
        raise HTTPException(status_code=400, detail="Not a voice channel")
    await db.voice_participants.update_one(
        {"channel_id": channel_id, "user_id": user["user_id"]},
        {"$set": {
            "channel_id": channel_id,
            "user_id": user["user_id"],
            "username": user["username"],
            "muted": False,
            "deafened": False,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True
    )
    participants = await db.voice_participants.find(
        {"channel_id": channel_id}, {"_id": 0}
    ).to_list(50)
    await sio.emit('voice_update', {
        "channel_id": channel_id,
        "participants": participants
    }, room=f"channel_{channel_id}")
    return {"participants": participants}

@fastapi_app.post("/api/channels/{channel_id}/voice/leave")
async def leave_voice_channel(channel_id: str, user: dict = Depends(get_current_user)):
    await db.voice_participants.delete_one({"channel_id": channel_id, "user_id": user["user_id"]})
    participants = await db.voice_participants.find(
        {"channel_id": channel_id}, {"_id": 0}
    ).to_list(50)
    await sio.emit('voice_update', {
        "channel_id": channel_id,
        "participants": participants
    }, room=f"channel_{channel_id}")
    return {"participants": participants}

@fastapi_app.get("/api/channels/{channel_id}/voice/participants")
async def get_voice_participants(channel_id: str, user: dict = Depends(get_current_user)):
    participants = await db.voice_participants.find(
        {"channel_id": channel_id}, {"_id": 0}
    ).to_list(50)
    return {"participants": participants}

# ============ SEARCH ============

@fastapi_app.get("/api/search")
async def search(q: str = "", user: dict = Depends(get_current_user)):
    if not q or len(q) < 2:
        return {"servers": [], "users": [], "messages": []}
    servers = await db.servers.find(
        {"name": {"$regex": q, "$options": "i"}}, {"_id": 0}
    ).limit(10).to_list(10)
    users = await db.users.find(
        {"username": {"$regex": q, "$options": "i"}},
        {"_id": 0, "password_hash": 0}
    ).limit(10).to_list(10)
    # Search messages in user's servers
    memberships = await db.server_members.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).to_list(100)
    server_ids = [m["server_id"] for m in memberships]
    messages = []
    if server_ids:
        messages = await db.messages.find(
            {"server_id": {"$in": server_ids}, "content": {"$regex": q, "$options": "i"}},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
    return {"servers": servers, "users": users, "messages": messages}

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
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@karasuworld.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "KarasuAdmin123!")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        admin_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": admin_id,
            "email": admin_email,
            "username": "KarasuAdmin",
            "password_hash": hash_password(admin_password),
            "bio": "System Administrator",
            "avatar_url": "",
            "status": "offline",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin user seeded: {admin_email}")
    # Write test credentials
    os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"# KarasuWorld Test Credentials\n\n")
        f.write(f"## Admin Account\n- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n")
        f.write(f"## Auth Endpoints\n- POST /api/auth/register\n- POST /api/auth/login\n- GET /api/auth/me\n- POST /api/auth/refresh\n")
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

# Wrap FastAPI with Socket.IO
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/api/socket.io')
