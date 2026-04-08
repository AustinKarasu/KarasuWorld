import React, { useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/AuthContext';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

interface DM {
  dm_id: string;
  last_message: string | null;
  last_message_at: string | null;
  other_user?: {
    user_id: string;
    username: string;
    avatar_url: string;
    is_online: boolean;
  };
}

export default function MessagesScreen() {
  const [dms, setDms] = useState<DM[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadDMs = async () => {
    try {
      const data = await api.get('/api/dms');
      setDms(data.dms || []);
    } catch (e) {
      console.error('Failed to load DMs:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadDMs(); }, []));

  const formatTime = (iso: string | null) => {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = diffMs / (1000 * 60 * 60);
    if (diffH < 1) return `${Math.max(1, Math.floor(diffMs / 60000))}m`;
    if (diffH < 24) return `${Math.floor(diffH)}h`;
    return `${Math.floor(diffH / 24)}d`;
  };

  const renderDM = ({ item }: { item: DM }) => (
    <TouchableOpacity
      testID={`dm-item-${item.dm_id}`}
      style={styles.dmCard}
      onPress={() => router.push(`/dm/${item.dm_id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.avatarContainer}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {item.other_user?.username?.[0]?.toUpperCase() || '?'}
          </Text>
        </View>
        {item.other_user?.is_online && <View style={styles.onlineDot} />}
      </View>
      <View style={styles.dmInfo}>
        <Text style={styles.dmName} numberOfLines={1}>
          {item.other_user?.username || 'Unknown'}
        </Text>
        <Text style={styles.dmMessage} numberOfLines={1}>
          {item.last_message || 'No messages yet'}
        </Text>
      </View>
      {item.last_message_at && (
        <Text style={styles.dmTime}>{formatTime(item.last_message_at)}</Text>
      )}
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Messages</Text>
      </View>
      {dms.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="chatbubbles-outline" size={64} color={Colors.text_tertiary} />
          <Text style={styles.emptyTitle}>No Messages</Text>
          <Text style={styles.emptySubtitle}>Start a conversation from a server member list</Text>
        </View>
      ) : (
        <FlatList
          data={dms}
          keyExtractor={(item) => item.dm_id}
          renderItem={renderDM}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadDMs(); }} tintColor={Colors.primary} />
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    paddingHorizontal: 20, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { fontSize: 28, fontWeight: '900', color: Colors.text_primary },
  list: { padding: 16, gap: 4 },
  dmCard: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    paddingVertical: 12, paddingHorizontal: 4,
  },
  avatarContainer: { position: 'relative' },
  avatar: {
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  avatarText: { color: Colors.text_primary, fontSize: 18, fontWeight: '700' },
  onlineDot: {
    position: 'absolute', bottom: 0, right: 0,
    width: 14, height: 14, borderRadius: 7,
    backgroundColor: Colors.online, borderWidth: 2, borderColor: Colors.bg_primary,
  },
  dmInfo: { flex: 1 },
  dmName: { fontSize: 15, fontWeight: '700', color: Colors.text_primary },
  dmMessage: { fontSize: 13, color: Colors.text_secondary, marginTop: 2 },
  dmTime: { fontSize: 11, color: Colors.text_tertiary },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: Colors.text_primary, marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: Colors.text_secondary, textAlign: 'center', marginTop: 8 },
});
