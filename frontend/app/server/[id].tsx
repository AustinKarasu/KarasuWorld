import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator, Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

interface Channel {
  channel_id: string;
  name: string;
  channel_type: string;
}

interface Member {
  user_id: string;
  username: string;
  role: string;
  is_online: boolean;
}

export default function ServerDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [server, setServer] = useState<any>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [showMembers, setShowMembers] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const router = useRouter();

  const loadData = async () => {
    try {
      const [serverData, channelData, memberData] = await Promise.all([
        api.get(`/api/servers/${id}`),
        api.get(`/api/servers/${id}/channels`),
        api.get(`/api/servers/${id}/members`),
      ]);
      setServer(serverData.server);
      setChannels(channelData.channels || []);
      setMembers(memberData.members || []);
    } catch (e: any) {
      Alert.alert('Error', e.message);
      router.back();
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(useCallback(() => { loadData(); }, [id]));

  const handleGetInvite = async () => {
    try {
      const data = await api.get(`/api/servers/${id}/invite`);
      setInviteCode(data.invite_code);
      setShowInvite(true);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const handleCreateChannel = () => {
    Alert.prompt?.('Create Channel', 'Enter channel name', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Create', onPress: async (name) => {
        if (!name?.trim()) return;
        try {
          await api.post(`/api/servers/${id}/channels`, { name: name.trim(), channel_type: 'text' });
          loadData();
        } catch (e: any) {
          Alert.alert('Error', e.message);
        }
      }},
    ]) || createChannelFallback();
  };

  const createChannelFallback = () => {
    // For platforms that don't support Alert.prompt
    router.push(`/create-channel?serverId=${id}`);
  };

  const startDM = async (userId: string) => {
    try {
      const data = await api.post('/api/dms', { recipient_id: userId });
      router.push(`/dm/${data.dm.dm_id}`);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const textChannels = channels.filter(c => c.channel_type === 'text');
  const voiceChannels = channels.filter(c => c.channel_type === 'voice');

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle} numberOfLines={1}>{server?.name}</Text>
          <Text style={styles.headerSubtitle}>{members.length} members</Text>
        </View>
        <TouchableOpacity testID="server-settings-btn" onPress={() => router.push(`/server-settings/${id}`)} style={styles.headerAction}>
          <Ionicons name="settings-outline" size={22} color={Colors.text_secondary} />
        </TouchableOpacity>
        <TouchableOpacity testID="invite-btn" onPress={handleGetInvite} style={styles.headerAction}>
          <Ionicons name="link-outline" size={22} color={Colors.text_secondary} />
        </TouchableOpacity>
        <TouchableOpacity testID="members-btn" onPress={() => setShowMembers(!showMembers)} style={styles.headerAction}>
          <Ionicons name="people-outline" size={22} color={showMembers ? Colors.primary : Colors.text_secondary} />
        </TouchableOpacity>
      </View>

      {showInvite && (
        <View style={styles.inviteBanner}>
          <Text style={styles.inviteLabel}>INVITE CODE</Text>
          <Text style={styles.inviteCode}>{inviteCode}</Text>
          <TouchableOpacity onPress={() => setShowInvite(false)}>
            <Ionicons name="close" size={18} color={Colors.text_tertiary} />
          </TouchableOpacity>
        </View>
      )}

      {showMembers ? (
        <FlatList
          data={members}
          keyExtractor={(item) => item.user_id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`member-${item.user_id}`}
              style={styles.memberRow}
              onPress={() => startDM(item.user_id)}
            >
              <View style={styles.memberAvatar}>
                <Text style={styles.memberAvatarText}>{item.username[0]?.toUpperCase()}</Text>
                <View style={[styles.memberStatus, { backgroundColor: item.is_online ? Colors.online : Colors.offline }]} />
              </View>
              <View style={styles.memberInfo}>
                <Text style={styles.memberName}>{item.username}</Text>
                <Text style={styles.memberRole}>{item.role}</Text>
              </View>
            </TouchableOpacity>
          )}
        />
      ) : (
        <FlatList
          data={[
            { type: 'section', title: 'TEXT CHANNELS', count: textChannels.length },
            ...textChannels.map(c => ({ type: 'channel', ...c })),
            { type: 'section', title: 'VOICE CHANNELS', count: voiceChannels.length },
            ...voiceChannels.map(c => ({ type: 'channel', ...c })),
          ]}
          keyExtractor={(item: any, idx) => item.channel_id || `section-${idx}`}
          contentContainerStyle={styles.list}
          renderItem={({ item }: { item: any }) => {
            if (item.type === 'section') {
              return (
                <View style={styles.sectionHeader}>
                  <Text style={styles.sectionTitle}>{item.title}</Text>
                  {(server?.my_role === 'admin' || server?.my_role === 'moderator') && (
                    <TouchableOpacity
                      testID={`add-channel-btn`}
                      onPress={() => router.push(`/create-channel?serverId=${id}&type=${item.title.includes('VOICE') ? 'voice' : 'text'}`)}
                    >
                      <Ionicons name="add" size={18} color={Colors.text_tertiary} />
                    </TouchableOpacity>
                  )}
                </View>
              );
            }
            return (
              <TouchableOpacity
                testID={`channel-${item.channel_id}`}
                style={styles.channelRow}
                onPress={() => {
                  if (item.channel_type === 'text') {
                    router.push(`/channel/${item.channel_id}`);
                  } else if (item.channel_type === 'voice') {
                    router.push(`/voice/${item.channel_id}`);
                  }
                }}
              >
                <Ionicons
                  name={item.channel_type === 'voice' ? 'volume-high-outline' : 'chatbox-outline'}
                  size={20}
                  color={Colors.text_secondary}
                />
                <Text style={styles.channelName}>{item.name}</Text>
                {item.channel_type === 'voice' && item.voice_participant_count > 0 && (
                  <View style={styles.voiceBadge}><Text style={styles.voiceBadgeText}>{item.voice_participant_count}</Text></View>
                )}
              </TouchableOpacity>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 12, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  backBtn: { padding: 4 },
  headerInfo: { flex: 1 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: Colors.text_primary },
  headerSubtitle: { fontSize: 12, color: Colors.text_secondary },
  headerAction: { padding: 6 },
  inviteBanner: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: Colors.surface, margin: 12, borderRadius: 10,
    padding: 12, borderWidth: 1, borderColor: Colors.border,
  },
  inviteLabel: { fontSize: 9, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1 },
  inviteCode: { flex: 1, fontSize: 15, fontWeight: '700', color: Colors.primary },
  list: { padding: 12, gap: 2 },
  sectionHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 12, paddingHorizontal: 4,
  },
  sectionTitle: { fontSize: 11, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1 },
  channelRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingVertical: 10, paddingHorizontal: 12,
    borderRadius: 8,
  },
  channelName: { fontSize: 15, color: Colors.text_secondary, fontWeight: '500' },
  voiceBadge: { backgroundColor: Colors.success + '20', borderRadius: 10, paddingHorizontal: 6, paddingVertical: 2 },
  voiceBadgeText: { fontSize: 11, color: Colors.success, fontWeight: '700' },
  memberRow: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingVertical: 8, paddingHorizontal: 4,
  },
  memberAvatar: {
    width: 40, height: 40, borderRadius: 20, position: 'relative',
    backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center',
  },
  memberAvatarText: { color: Colors.text_primary, fontSize: 16, fontWeight: '700' },
  memberStatus: {
    position: 'absolute', bottom: 0, right: 0,
    width: 12, height: 12, borderRadius: 6,
    borderWidth: 2, borderColor: Colors.bg_primary,
  },
  memberInfo: { flex: 1 },
  memberName: { fontSize: 14, fontWeight: '600', color: Colors.text_primary },
  memberRole: { fontSize: 11, color: Colors.text_tertiary, textTransform: 'capitalize' },
});
