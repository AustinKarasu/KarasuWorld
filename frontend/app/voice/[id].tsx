import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, FlatList, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { io } from 'socket.io-client';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';
import { useAuth } from '@/src/AuthContext';

interface VoiceParticipant {
  user_id: string;
  username: string;
  muted: boolean;
  deafened: boolean;
}

export default function VoiceChannelScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
  const [participants, setParticipants] = useState<VoiceParticipant[]>([]);
  const [joined, setJoined] = useState(false);
  const [muted, setMuted] = useState(false);
  const [deafened, setDeafened] = useState(false);
  const router = useRouter();

  useEffect(() => {
    loadParticipants();
    if (!BACKEND_URL) {
      return () => {};
    }

    const socket = io(BACKEND_URL, {
      path: '/api/socket.io',
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      socket.emit('join_voice', { channel_id: id });
    });
    socket.on('voice_update', (payload: { channel_id: string; participants: VoiceParticipant[] }) => {
      if (payload?.channel_id === id) {
        setParticipants(payload.participants || []);
      }
    });
    socket.on('voice_user_joined', () => loadParticipants());
    socket.on('voice_user_left', () => loadParticipants());

    const pollTimer = setInterval(loadParticipants, 5000);
    return () => {
      clearInterval(pollTimer);
      socket.emit('leave_voice', { channel_id: id });
      socket.disconnect();
    };
  }, [id]);

  useEffect(() => {
    return () => {
      if (joined) {
        leaveVoice();
      }
    };
  }, [joined]);

  const loadParticipants = async () => {
    try {
      const data = await api.get(`/api/channels/${id}/voice/participants`);
      setParticipants(data.participants || []);
      setJoined(data.participants?.some((p: any) => p.user_id === user?.user_id) || false);
    } catch {}
  };

  const joinVoice = async () => {
    try {
      const data = await api.post(`/api/channels/${id}/voice/join`);
      setParticipants(data.participants || []);
      setJoined(true);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const leaveVoice = async () => {
    try {
      const data = await api.post(`/api/channels/${id}/voice/leave`);
      setParticipants(data.participants || []);
      setJoined(false);
      setMuted(false);
      setDeafened(false);
    } catch {}
  };

  const toggleMute = async () => {
    const newMuted = !muted;
    setMuted(newMuted);
    try {
      const data = await api.post(`/api/channels/${id}/voice/toggle`, { muted: newMuted });
      setParticipants(data.participants || []);
    } catch {}
  };

  const toggleDeafen = async () => {
    const newDeafened = !deafened;
    setDeafened(newDeafened);
    const nextMuted = newDeafened || muted;
    if (newDeafened && !muted) setMuted(true);
    try {
      const data = await api.post(`/api/channels/${id}/voice/toggle`, { deafened: newDeafened, muted: nextMuted });
      setParticipants(data.participants || []);
    } catch {}
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="voice-back-btn" onPress={() => { if (joined) leaveVoice(); router.back(); }}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <Ionicons name="volume-high" size={18} color={Colors.success} />
        <Text style={styles.headerTitle}>Voice Channel</Text>
      </View>

      <View style={styles.center}>
        {!joined ? (
          <View style={styles.joinSection}>
            <View style={styles.voiceIcon}>
              <Ionicons name="volume-high-outline" size={64} color={Colors.primary} />
            </View>
            <Text style={styles.joinTitle}>Voice Channel</Text>
            <Text style={styles.joinSubtitle}>{participants.length} participant{participants.length !== 1 ? 's' : ''} connected</Text>
            <TouchableOpacity testID="join-voice-btn" style={styles.joinBtn} onPress={joinVoice}>
              <Ionicons name="call" size={20} color="#FFF" />
              <Text style={styles.joinBtnText}>Join Voice</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.connectedSection}>
            <View style={styles.connectedBadge}>
              <Ionicons name="radio-outline" size={16} color={Colors.success} />
              <Text style={styles.connectedText}>Voice Connected</Text>
            </View>

            <FlatList
              data={participants}
              keyExtractor={(item) => item.user_id}
              contentContainerStyle={styles.participantList}
              numColumns={3}
              renderItem={({ item }) => (
                <View testID={`voice-participant-${item.user_id}`} style={styles.participantCard}>
                  <View style={[styles.participantAvatar, item.user_id === user?.user_id && { borderColor: Colors.primary, borderWidth: 2 }]}>
                    <Text style={styles.participantAvatarText}>{item.username?.[0]?.toUpperCase()}</Text>
                    {item.muted && (
                      <View style={styles.mutedBadge}><Ionicons name="mic-off" size={10} color={Colors.error} /></View>
                    )}
                  </View>
                  <Text style={styles.participantName} numberOfLines={1}>{item.username}</Text>
                  {item.deafened && <Ionicons name="volume-mute" size={12} color={Colors.error} />}
                </View>
              )}
            />

            <View style={styles.controls}>
              <TouchableOpacity testID="toggle-mute-btn" style={[styles.controlBtn, muted && styles.controlBtnActive]} onPress={toggleMute}>
                <Ionicons name={muted ? 'mic-off' : 'mic'} size={24} color={muted ? Colors.error : Colors.text_primary} />
                <Text style={[styles.controlLabel, muted && { color: Colors.error }]}>{muted ? 'Unmute' : 'Mute'}</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="toggle-deafen-btn" style={[styles.controlBtn, deafened && styles.controlBtnActive]} onPress={toggleDeafen}>
                <Ionicons name={deafened ? 'volume-mute' : 'volume-high'} size={24} color={deafened ? Colors.error : Colors.text_primary} />
                <Text style={[styles.controlLabel, deafened && { color: Colors.error }]}>{deafened ? 'Undeafen' : 'Deafen'}</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="leave-voice-btn" style={[styles.controlBtn, { backgroundColor: Colors.error + '20' }]} onPress={() => { leaveVoice(); router.back(); }}>
                <Ionicons name="call" size={24} color={Colors.error} />
                <Text style={[styles.controlLabel, { color: Colors.error }]}>Leave</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { fontSize: 17, fontWeight: '700', color: Colors.text_primary, flex: 1 },
  center: { flex: 1 },
  joinSection: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  voiceIcon: { width: 120, height: 120, borderRadius: 60, backgroundColor: Colors.surface, justifyContent: 'center', alignItems: 'center', marginBottom: 24, borderWidth: 1, borderColor: Colors.border },
  joinTitle: { fontSize: 22, fontWeight: '800', color: Colors.text_primary },
  joinSubtitle: { fontSize: 14, color: Colors.text_secondary, marginTop: 4 },
  joinBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: Colors.success, borderRadius: 24, paddingHorizontal: 32, paddingVertical: 14, marginTop: 24 },
  joinBtnText: { color: '#FFF', fontWeight: '700', fontSize: 16 },
  connectedSection: { flex: 1, paddingTop: 16 },
  connectedBadge: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 8 },
  connectedText: { color: Colors.success, fontSize: 13, fontWeight: '600' },
  participantList: { padding: 16, justifyContent: 'center' },
  participantCard: { alignItems: 'center', padding: 8, width: '33%' },
  participantAvatar: { width: 64, height: 64, borderRadius: 32, backgroundColor: Colors.surface, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  participantAvatarText: { color: Colors.text_primary, fontSize: 24, fontWeight: '700' },
  mutedBadge: { position: 'absolute', bottom: 0, right: 0, width: 20, height: 20, borderRadius: 10, backgroundColor: Colors.bg_primary, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: Colors.border },
  participantName: { fontSize: 12, color: Colors.text_secondary, marginTop: 4 },
  controls: { flexDirection: 'row', justifyContent: 'center', gap: 24, paddingVertical: 24, paddingBottom: 40, borderTopWidth: 1, borderTopColor: Colors.border },
  controlBtn: { alignItems: 'center', gap: 4, padding: 12, borderRadius: 16, backgroundColor: Colors.surface, minWidth: 72 },
  controlBtnActive: { backgroundColor: Colors.error + '10' },
  controlLabel: { fontSize: 11, color: Colors.text_secondary, fontWeight: '600' },
});
