# KarasuWorld - Product Requirements Document

## Overview
KarasuWorld is a Discord-inspired real-time communication and community-building mobile application built with Expo React Native and FastAPI backend.

## Tech Stack
- **Frontend**: Expo React Native (SDK 54) with expo-router, Socket.IO client
- **Backend**: FastAPI with python-socketio for WebSocket support
- **Database**: MongoDB (motor async driver)
- **Authentication**: JWT (email/password) with bcrypt password hashing
- **Real-time**: Socket.IO for messaging, typing indicators, and online status

## Core Features Implemented

### 1. Authentication
- Email/password registration and login
- JWT access tokens (7-day expiry) + refresh tokens (30-day)
- Admin account auto-seeded on startup
- Profile edit (username, bio)

### 2. Servers (Communities)
- Create servers with name, description, auto-generated icon
- Join servers via invite codes
- Role-based permissions (admin, moderator, member)
- Member list with online/offline status
- Server invite code generation

### 3. Channels
- Text channels with real-time messaging
- Voice channels (UI/endpoints ready, WebRTC integration for later)
- Create/delete channels (admin/moderator only)
- Default "general" channel auto-created with each server

### 4. Real-time Messaging
- Socket.IO WebSocket integration
- Message sending with instant broadcast to channel members
- Emoji reactions on messages (👍 ❤️ 😂 🔥 😮 😢)
- Typing indicators
- Message history with pagination support

### 5. Direct Messages
- Private 1-on-1 conversations
- Real-time DM delivery via Socket.IO
- DM list with last message preview and timestamps
- Typing indicators in DMs

### 6. User Profiles
- Username, email, bio, avatar
- Online/offline status tracking via WebSocket
- Profile editing

### 7. Search & Discovery
- Global search across servers, users, and messages
- User search for starting DMs

### 8. Navigation
- Tab-based navigation: Servers, Messages, Search, Profile
- Stack navigation for server details, channels, chats
- Modal screens for create/join server, create channel

## API Endpoints
- Auth: /api/auth/register, login, me, refresh
- Servers: CRUD, join, invite, members
- Channels: CRUD within servers
- Messages: Send, list, reactions
- DMs: Create, list, send messages
- Users: Profile, search
- Search: Global search

## Future Enhancements
- Google OAuth integration (Emergent Auth ready)
- GIF/Sticker support (Giphy/Tenor - pending API keys)
- Voice channel WebRTC audio streaming
- Push notifications (Firebase Cloud Messaging)
- Media/file sharing
- Bot integration system
- Admin dashboard
- End-to-end encryption for DMs

## Design
- Dark theme (Archetype 2: Performance Pro)
- Deep obsidian (#0A0A0A) background with volt blue (#007AFF) accents
- High-contrast text for readability during long sessions
