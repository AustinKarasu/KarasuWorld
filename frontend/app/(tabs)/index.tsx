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

interface Server {
  server_id: string;
  name: string;
  description: string;
  icon_letter: string;
  member_count: number;
  my_role: string;
}

export default function ServersScreen() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { user } = useAuth();
  const router = useRouter();

  const loadServers = async () => {
    try {
      const data = await api.get('/api/servers');
      setServers(data.servers || []);
    } catch (e) {
      console.error('Failed to load servers:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadServers(); }, []));

  const onRefresh = () => {
    setRefreshing(true);
    loadServers();
  };

  const renderServer = ({ item }: { item: Server }) => (
    <TouchableOpacity
      testID={`server-item-${item.server_id}`}
      style={styles.serverCard}
      onPress={() => router.push(`/server/${item.server_id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.serverIcon}>
        <Text style={styles.serverIconText}>{item.icon_letter || item.name[0]}</Text>
      </View>
      <View style={styles.serverInfo}>
        <Text style={styles.serverName} numberOfLines={1}>{item.name}</Text>
        <Text style={styles.serverMeta}>
          {item.member_count} {item.member_count === 1 ? 'member' : 'members'} · {item.my_role}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={Colors.text_tertiary} />
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
        <Text style={styles.headerTitle}>Servers</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity
            testID="join-server-btn"
            style={styles.headerBtn}
            onPress={() => router.push('/join-server')}
          >
            <Ionicons name="enter-outline" size={22} color={Colors.text_primary} />
          </TouchableOpacity>
          <TouchableOpacity
            testID="create-server-btn"
            style={styles.headerBtn}
            onPress={() => router.push('/create-server')}
          >
            <Ionicons name="add-circle-outline" size={24} color={Colors.primary} />
          </TouchableOpacity>
        </View>
      </View>

      {servers.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="planet-outline" size={64} color={Colors.text_tertiary} />
          <Text style={styles.emptyTitle}>No Servers Yet</Text>
          <Text style={styles.emptySubtitle}>Create a server or join one with an invite code</Text>
          <TouchableOpacity
            testID="empty-create-server-btn"
            style={styles.emptyBtn}
            onPress={() => router.push('/create-server')}
          >
            <Ionicons name="add" size={20} color="#FFF" />
            <Text style={styles.emptyBtnText}>Create Server</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={servers}
          keyExtractor={(item) => item.server_id}
          renderItem={renderServer}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
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
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { fontSize: 28, fontWeight: '900', color: Colors.text_primary },
  headerActions: { flexDirection: 'row', gap: 12 },
  headerBtn: { padding: 4 },
  list: { padding: 16, gap: 8 },
  serverCard: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    backgroundColor: Colors.surface, borderRadius: 12, padding: 14,
    borderWidth: 1, borderColor: Colors.border,
  },
  serverIcon: {
    width: 48, height: 48, borderRadius: 14,
    backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center',
  },
  serverIconText: { color: '#FFF', fontSize: 20, fontWeight: '800' },
  serverInfo: { flex: 1 },
  serverName: { fontSize: 16, fontWeight: '700', color: Colors.text_primary },
  serverMeta: { fontSize: 12, color: Colors.text_secondary, marginTop: 2 },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: Colors.text_primary, marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: Colors.text_secondary, textAlign: 'center', marginTop: 8 },
  emptyBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: Colors.primary, borderRadius: 8,
    paddingHorizontal: 20, paddingVertical: 12, marginTop: 24,
  },
  emptyBtnText: { color: '#FFF', fontWeight: '700', fontSize: 15 },
});
