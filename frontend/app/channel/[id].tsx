import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, FlatList,
  KeyboardAvoidingView, Platform, ActivityIndicator, ScrollView, Image,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { io, Socket } from 'socket.io-client';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';
import { useAuth } from '@/src/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface Message {
  message_id: string;
  channel_id?: string;
  sender_id: string;
  sender_username: string;
  content: string;
  message_type: string;
  media_url?: string;
  media_type?: string;
  reactions: Array<{ emoji: string; users: string[]; count: number }>;
  created_at: string;
}

const EMOJI_OPTIONS = ['👍', '❤️', '😂', '🔥', '😮', '😢'];

export default function ChannelChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [channelName, setChannelName] = useState('');
  const [typingUser, setTypingUser] = useState('');
  const [showReactions, setShowReactions] = useState<string | null>(null);
  const [showStickers, setShowStickers] = useState(false);
  const [stickers, setStickers] = useState<any[]>([]);
  const socketRef = useRef<Socket | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  useEffect(() => {
    loadMessages();
    connectSocket();
    return () => {
      if (socketRef.current?.connected) {
        socketRef.current.emit('leave_channel', { channel_id: id });
        socketRef.current.disconnect();
      }
    };
  }, [id]);

  const loadMessages = async () => {
    try {
      const data = await api.get(`/api/channels/${id}/messages`);
      setMessages(data.messages || []);
      // Try to get channel name from the first message's context
    } catch (e) {
      console.error('Failed to load messages:', e);
    } finally {
      setLoading(false);
    }
  };

  const connectSocket = async () => {
    const token = await AsyncStorage.getItem('access_token');
    if (!token) return;
    const socket = io(BACKEND_URL, {
      path: '/api/socket.io',
      auth: { token },
      transports: ['websocket', 'polling'],
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('join_channel', { channel_id: id });
    });

    socket.on('new_message', (msg: Message) => {
      if (msg.channel_id === id) {
        setMessages(prev => [...prev, msg]);
      }
    });

    socket.on('reaction_update', (data: { message_id: string; reactions: any[] }) => {
      setMessages(prev => prev.map(m =>
        m.message_id === data.message_id ? { ...m, reactions: data.reactions } : m
      ));
    });

    socket.on('user_typing', (data: { username: string; channel_id: string }) => {
      if (data.channel_id === id) {
        setTypingUser(data.username);
        if (typingTimeout.current) clearTimeout(typingTimeout.current);
        typingTimeout.current = setTimeout(() => setTypingUser(''), 3000);
      }
    });
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    const content = input.trim();
    setInput('');
    setShowStickers(false);
    try {
      await api.post(`/api/channels/${id}/messages`, { content, message_type: 'text' });
    } catch (e) {
      console.error('Failed to send message:', e);
    }
  };

  const sendSticker = async (emoji: string) => {
    setShowStickers(false);
    try {
      await api.post(`/api/channels/${id}/messages`, { content: emoji, message_type: 'sticker' });
    } catch (e) {
      console.error('Failed to send sticker:', e);
    }
  };

  const pickAndSendImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.5, base64: true });
    if (!result.canceled && result.assets[0].base64) {
      try {
        const uploadResp = await api.post('/api/upload', {
          data: result.assets[0].base64,
          filename: 'image.jpg',
          content_type: 'image/jpeg',
        });
        await api.post(`/api/channels/${id}/messages`, {
          content: '📷 Image', message_type: 'image',
          media_url: uploadResp.url, media_type: 'image/jpeg',
        });
      } catch (e) {
        console.error('Image upload failed:', e);
      }
    }
  };

  const loadStickers = async () => {
    try {
      const data = await api.get('/api/stickers');
      setStickers(data.sticker_packs || []);
    } catch {}
  };

  const handleTyping = () => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('typing', { channel_id: id });
    }
  };

  const toggleReaction = async (messageId: string, emoji: string) => {
    try {
      const msg = messages.find(m => m.message_id === messageId);
      const existingReaction = msg?.reactions?.find(r => r.emoji === emoji);
      const hasReacted = existingReaction?.users?.includes(user?.user_id || '');
      if (hasReacted) {
        await api.delete(`/api/messages/${messageId}/react/${encodeURIComponent(emoji)}`);
      } else {
        await api.post(`/api/messages/${messageId}/react`, { emoji });
      }
      setShowReactions(null);
    } catch (e) {
      console.error('Reaction error:', e);
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const renderMessage = ({ item, index }: { item: Message; index: number }) => {
    const isMe = item.sender_id === user?.user_id;
    const prevMsg = index > 0 ? messages[index - 1] : null;
    const showHeader = !prevMsg || prevMsg.sender_id !== item.sender_id;

    return (
      <TouchableOpacity
        testID={`message-${item.message_id}`}
        style={styles.messageRow}
        onLongPress={() => setShowReactions(showReactions === item.message_id ? null : item.message_id)}
        activeOpacity={0.8}
      >
        {showHeader && (
          <View style={styles.msgHeader}>
            <View style={[styles.msgAvatar, isMe && { backgroundColor: Colors.primary }]}>
              <Text style={styles.msgAvatarText}>{item.sender_username?.[0]?.toUpperCase()}</Text>
            </View>
            <Text style={styles.msgUsername}>{item.sender_username}</Text>
            <Text style={styles.msgTime}>{formatTime(item.created_at)}</Text>
          </View>
        )}
        <View style={[styles.msgContent, !showHeader && { marginLeft: 44 }]}>
          {item.message_type === 'sticker' ? (
            <Text style={styles.stickerMsg}>{item.content}</Text>
          ) : item.message_type === 'image' && item.media_url ? (
            <View>
              <Image source={{ uri: `${BACKEND_URL}${item.media_url}` }} style={styles.mediaImage} resizeMode="cover" />
            </View>
          ) : (
            <Text style={styles.msgText}>{item.content}</Text>
          )}
        </View>

        {item.reactions && item.reactions.length > 0 && (
          <View style={[styles.reactionsRow, !showHeader && { marginLeft: 44 }]}>
            {item.reactions.map((r, i) => (
              <TouchableOpacity
                key={i}
                style={[styles.reactionBadge, r.users?.includes(user?.user_id || '') && styles.reactionActive]}
                onPress={() => toggleReaction(item.message_id, r.emoji)}
              >
                <Text style={styles.reactionText}>{r.emoji} {r.count}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {showReactions === item.message_id && (
          <View style={[styles.reactionPicker, !showHeader && { marginLeft: 44 }]}>
            {EMOJI_OPTIONS.map(emoji => (
              <TouchableOpacity
                key={emoji}
                style={styles.emojiBtn}
                onPress={() => toggleReaction(item.message_id, emoji)}
              >
                <Text style={styles.emojiBtnText}>{emoji}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="chat-back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <Ionicons name="chatbox-outline" size={18} color={Colors.text_secondary} />
        <Text style={styles.headerTitle} numberOfLines={1}>{channelName || 'Channel'}</Text>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
        keyboardVerticalOffset={0}
      >
        {loading ? (
          <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.message_id}
            renderItem={renderMessage}
            contentContainerStyle={styles.messageList}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
            ListEmptyComponent={
              <View style={styles.emptyChat}>
                <Ionicons name="chatbox-outline" size={48} color={Colors.text_tertiary} />
                <Text style={styles.emptyChatText}>No messages yet. Start the conversation!</Text>
              </View>
            }
          />
        )}

        {typingUser ? (
          <View style={styles.typingBar}>
            <Text style={styles.typingText}>{typingUser} is typing...</Text>
          </View>
        ) : null}

        <View style={styles.inputBar}>
          <TouchableOpacity testID="sticker-btn" style={styles.attachBtn} onPress={() => { if (!stickers.length) loadStickers(); setShowStickers(!showStickers); }}>
            <Ionicons name="happy-outline" size={22} color={showStickers ? Colors.primary : Colors.text_tertiary} />
          </TouchableOpacity>
          <TouchableOpacity testID="media-btn" style={styles.attachBtn} onPress={pickAndSendImage}>
            <Ionicons name="image-outline" size={22} color={Colors.text_tertiary} />
          </TouchableOpacity>
          <TextInput
            testID="chat-input"
            style={styles.chatInput}
            value={input}
            onChangeText={(text) => { setInput(text); handleTyping(); }}
            placeholder="Type a message..."
            placeholderTextColor={Colors.text_tertiary}
            multiline
            maxLength={4000}
          />
          <TouchableOpacity
            testID="send-message-btn"
            style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
            onPress={sendMessage}
            disabled={!input.trim()}
          >
            <Ionicons name="send" size={20} color={input.trim() ? '#FFF' : Colors.text_tertiary} />
          </TouchableOpacity>
        </View>

        {showStickers && (
          <View style={styles.stickerPicker}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.stickerScroll}>
              {stickers.map((pack, pi) => (
                <View key={pi} style={styles.stickerPack}>
                  <Text style={styles.stickerPackTitle}>{pack.pack}</Text>
                  <View style={styles.stickerGrid}>
                    {pack.stickers?.map((s: any) => (
                      <TouchableOpacity key={s.id} style={styles.stickerItem} onPress={() => sendSticker(s.emoji)}>
                        <Text style={styles.stickerEmoji}>{s.emoji}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  flex: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 12, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  backBtn: { padding: 4 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: Colors.text_primary, flex: 1 },
  messageList: { padding: 12, paddingBottom: 4, flexGrow: 1 },
  messageRow: { marginBottom: 4 },
  msgHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4, marginTop: 8 },
  msgAvatar: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center',
  },
  msgAvatarText: { color: Colors.text_primary, fontSize: 14, fontWeight: '700' },
  msgUsername: { fontSize: 14, fontWeight: '700', color: Colors.text_primary },
  msgTime: { fontSize: 11, color: Colors.text_tertiary },
  msgContent: { marginLeft: 44 },
  msgText: { fontSize: 15, color: Colors.text_primary, lineHeight: 21 },
  stickerMsg: { fontSize: 48 },
  mediaImage: { width: 200, height: 200, borderRadius: 12, marginTop: 4 },
  reactionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 4, marginLeft: 44 },
  reactionBadge: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: Colors.surface, borderRadius: 12,
    paddingHorizontal: 8, paddingVertical: 4,
    borderWidth: 1, borderColor: Colors.border,
  },
  reactionActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,122,255,0.15)' },
  reactionText: { fontSize: 12, color: Colors.text_primary },
  reactionPicker: {
    flexDirection: 'row', gap: 4, marginTop: 4, marginLeft: 44,
    backgroundColor: Colors.surface, borderRadius: 12, padding: 6,
    borderWidth: 1, borderColor: Colors.border,
  },
  emojiBtn: { padding: 6 },
  emojiBtnText: { fontSize: 20 },
  typingBar: { paddingHorizontal: 16, paddingVertical: 4 },
  typingText: { fontSize: 12, color: Colors.text_tertiary, fontStyle: 'italic' },
  inputBar: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    paddingHorizontal: 12, paddingVertical: 8,
    borderTopWidth: 1, borderTopColor: Colors.border,
    backgroundColor: Colors.bg_secondary,
  },
  chatInput: {
    flex: 1, backgroundColor: Colors.bg_tertiary, borderRadius: 20,
    paddingHorizontal: 16, paddingVertical: 10, paddingRight: 16,
    color: Colors.text_primary, fontSize: 15, maxHeight: 100,
    borderWidth: 1, borderColor: Colors.border,
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center',
  },
  sendBtnDisabled: { backgroundColor: Colors.surface },
  attachBtn: { padding: 6, justifyContent: 'center', alignItems: 'center' },
  stickerPicker: {
    backgroundColor: Colors.bg_secondary, borderTopWidth: 1, borderTopColor: Colors.border,
    maxHeight: 180,
  },
  stickerScroll: { padding: 8, gap: 16 },
  stickerPack: { marginRight: 12 },
  stickerPackTitle: { fontSize: 10, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1, marginBottom: 6, textTransform: 'uppercase' },
  stickerGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  stickerItem: { width: 44, height: 44, justifyContent: 'center', alignItems: 'center', borderRadius: 8, backgroundColor: Colors.surface },
  stickerEmoji: { fontSize: 24 },
  emptyChat: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyChatText: { fontSize: 14, color: Colors.text_secondary },
});
