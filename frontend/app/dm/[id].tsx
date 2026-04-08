import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, FlatList,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { io, Socket } from 'socket.io-client';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';
import { useAuth } from '@/src/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface DMMessage {
  message_id: string;
  sender_id: string;
  sender_username: string;
  content: string;
  created_at: string;
}

export default function DMChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<DMMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [otherUser, setOtherUser] = useState<string>('');
  const [typingUser, setTypingUser] = useState('');
  const socketRef = useRef<Socket | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  useEffect(() => {
    loadMessages();
    connectSocket();
    return () => {
      if (socketRef.current?.connected) {
        socketRef.current.emit('leave_dm', { dm_id: id });
        socketRef.current.disconnect();
      }
    };
  }, [id]);

  const loadMessages = async () => {
    try {
      const [msgData, dmData] = await Promise.all([
        api.get(`/api/dms/${id}/messages`),
        api.get('/api/dms'),
      ]);
      setMessages(msgData.messages || []);
      const dm = dmData.dms?.find((d: any) => d.dm_id === id);
      if (dm?.other_user) {
        setOtherUser(dm.other_user.username);
      }
    } catch (e) {
      console.error('Failed to load DM messages:', e);
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
      socket.emit('join_dm', { dm_id: id });
    });

    socket.on('new_dm_message', (msg: DMMessage) => {
      if (msg.dm_id === id) {
        setMessages(prev => [...prev, msg]);
      }
    });

    socket.on('user_typing', (data: { username: string; dm_id: string }) => {
      if (data.dm_id === id) {
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
    try {
      await api.post(`/api/dms/${id}/messages`, { content, message_type: 'text' });
    } catch (e) {
      console.error('Failed to send DM:', e);
    }
  };

  const handleTyping = () => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('typing', { dm_id: id });
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const renderMessage = ({ item }: { item: DMMessage }) => {
    const isMe = item.sender_id === user?.user_id;
    return (
      <View testID={`dm-message-${item.message_id}`} style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleOther]}>
        <Text style={[styles.bubbleText, isMe && styles.bubbleTextMe]}>{item.content}</Text>
        <Text style={[styles.bubbleTime, isMe && styles.bubbleTimeMe]}>{formatTime(item.created_at)}</Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="dm-back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <View style={styles.headerAvatar}>
          <Text style={styles.headerAvatarText}>{otherUser?.[0]?.toUpperCase() || '?'}</Text>
        </View>
        <Text style={styles.headerTitle}>{otherUser || 'Direct Message'}</Text>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
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
                <Ionicons name="chatbubble-ellipses-outline" size={48} color={Colors.text_tertiary} />
                <Text style={styles.emptyChatText}>Say hello!</Text>
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
          <TextInput
            testID="dm-chat-input"
            style={styles.chatInput}
            value={input}
            onChangeText={(text) => { setInput(text); handleTyping(); }}
            placeholder="Type a message..."
            placeholderTextColor={Colors.text_tertiary}
            multiline
            maxLength={2000}
          />
          <TouchableOpacity
            testID="dm-send-btn"
            style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
            onPress={sendMessage}
            disabled={!input.trim()}
          >
            <Ionicons name="send" size={20} color={input.trim() ? '#FFF' : Colors.text_tertiary} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  flex: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingHorizontal: 12, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  backBtn: { padding: 4 },
  headerAvatar: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center',
  },
  headerAvatarText: { color: Colors.text_primary, fontSize: 14, fontWeight: '700' },
  headerTitle: { fontSize: 17, fontWeight: '700', color: Colors.text_primary, flex: 1 },
  messageList: { padding: 12, paddingBottom: 4, flexGrow: 1 },
  bubble: { maxWidth: '80%', marginBottom: 8, borderRadius: 18, padding: 12 },
  bubbleMe: {
    alignSelf: 'flex-end', backgroundColor: Colors.primary,
    borderBottomRightRadius: 4,
  },
  bubbleOther: {
    alignSelf: 'flex-start', backgroundColor: Colors.surface,
    borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.border,
  },
  bubbleText: { fontSize: 15, color: Colors.text_primary, lineHeight: 21 },
  bubbleTextMe: { color: '#FFF' },
  bubbleTime: { fontSize: 10, color: Colors.text_tertiary, marginTop: 4, alignSelf: 'flex-end' },
  bubbleTimeMe: { color: 'rgba(255,255,255,0.7)' },
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
    paddingHorizontal: 16, paddingVertical: 10,
    color: Colors.text_primary, fontSize: 15, maxHeight: 100,
    borderWidth: 1, borderColor: Colors.border,
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center',
  },
  sendBtnDisabled: { backgroundColor: Colors.surface },
  emptyChat: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyChatText: { fontSize: 14, color: Colors.text_secondary },
});
