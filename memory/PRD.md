# KarasuWorld - Product Requirements Document (v2)

## Overview
KarasuWorld is a Discord-inspired real-time communication and community-building mobile app built with Expo React Native and FastAPI backend. Free forever - no premium tiers.

## Tech Stack
- **Frontend**: Expo React Native (SDK 54) with expo-router, Socket.IO client, crypto-js (E2EE)
- **Backend**: FastAPI with python-socketio for WebSocket, slowapi for rate limiting
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT (email/password) + Emergent Google OAuth
- **Real-time**: Socket.IO for messaging, typing indicators, online status, voice signaling
- **Encryption**: AES-256 for DM end-to-end encryption

## Core Features

### 1. Authentication
- Email/password registration with 8-char minimum, input validation, XSS sanitization
- JWT access tokens (7-day) + refresh tokens (30-day)
- Google OAuth via Emergent Auth (configurable via config.json)
- Rate limiting (60 req/min per IP)

### 2. Servers (Communities)
- Create servers with name, description, auto-generated icon
- Join via invite codes
- Auto-creates both #general text channel and General Voice channel
- Server settings for role management

### 3. Discord-like Role System
- 16 granular permissions: administrator, manage_server, manage_channels, manage_roles, manage_members, kick/ban_members, send_messages, manage_messages, add_reactions, connect_voice, speak, mute/deafen_members, mention_everyone, attach_files, view_channels
- Custom role creation with colors
- Default @everyone and Admin roles
- Role assignment to members

### 4. Channels
- Text channels with real-time messaging
- Voice channels with join/leave/mute/deafen
- WebRTC signaling via Socket.IO (offer/answer/ICE candidate exchange)

### 5. Real-time Messaging
- Socket.IO WebSocket messaging
- Sticker support (26 built-in emoji stickers in 3 packs: reactions, animals, gestures)
- Media/image sharing (upload via base64, stored in MongoDB)
- Message reactions (6 emoji options)
- Message deletion with permission checks
- Typing indicators
- Mentions support

### 6. Direct Messages with E2E Encryption
- AES-256 encryption with key exchange
- E2E key storage and retrieval
- Encrypted flag on DM conversations
- Lock icon indicator in UI

### 7. Friend System
- Send/accept/decline friend requests
- Friends list with online status
- Remove friends
- Start DM from friend list

### 8. User Profiles
- Avatar upload (base64 image picker)
- Banner upload
- Display name, username, bio
- Online/offline status tracking

### 9. Push Notifications
- Expo push token registration
- Notifications for channel messages and DMs
- Sent to offline users via Expo Push Service

### 10. Search & Discovery
- Global search across servers, users, messages

### 11. Security
- Rate limiting (60 req/min)
- Input sanitization (XSS prevention)
- Password minimum 8 characters
- JWT token validation
- Permission-based access control
- File size limits (10MB max)
- Regex injection prevention in search

## Configuration (config.json)
- Google Auth credentials (configurable by user)
- Supabase credentials (ready for migration)
- Giphy/Tenor API keys (for future GIF search)
- Push notification settings
- Security settings (rate limits, upload sizes, message length)

## API Endpoints
- Auth: register, login, me, refresh, google
- Servers: CRUD, join, invite, members
- Channels: CRUD, voice join/leave/toggle/participants
- Messages: CRUD, reactions, deletion
- DMs: CRUD, messages, E2E key exchange
- Friends: request, accept, decline, remove, list
- Roles: CRUD with permissions
- Upload: file upload and retrieval
- Stickers: built-in sticker packs
- GIFs: search (requires API keys)
- Push: token registration
- Search: global search
- Users: profile, update, search

## Future Enhancements
- WebRTC audio streaming (signaling ready)
- Supabase storage migration (config ready)
- Giphy/Tenor GIF search (config ready)
- Video channels
- Server bans
- Custom emoji packs
- Thread replies
- Admin dashboard
