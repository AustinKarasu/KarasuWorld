import React, { useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, TextInput,
  ActivityIndicator, Alert, RefreshControl,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

type Tab = 'friends' | 'pending' | 'add';

export default function FriendsScreen() {
  const [tab, setTab] = useState<Tab>('friends');
  const [friends, setFriends] = useState<any[]>([]);
  const [incoming, setIncoming] = useState<any[]>([]);
  const [outgoing, setOutgoing] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadData = async () => {
    try {
      const [friendsData, requestsData] = await Promise.all([
        api.get('/api/friends'),
        api.get('/api/friends/requests'),
      ]);
      setFriends(friendsData.friends || []);
      setIncoming(requestsData.incoming || []);
      setOutgoing(requestsData.outgoing || []);
    } catch (e) {
      console.error('Failed to load friends:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadData(); }, []));

  const searchUsers = async () => {
    if (!searchQuery.trim() || searchQuery.trim().length < 2) return;
    try {
      const data = await api.get(`/api/users/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchResults(data.users || []);
    } catch (e) {
      console.error('Search failed:', e);
    }
  };

  const sendFriendRequest = async (userId: string) => {
    try {
      await api.post('/api/friends/request', { target_user_id: userId });
      Alert.alert('Sent', 'Friend request sent!');
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const acceptRequest = async (friendshipId: string) => {
    try {
      await api.post(`/api/friends/${friendshipId}/accept`);
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const declineRequest = async (friendshipId: string) => {
    try {
      await api.post(`/api/friends/${friendshipId}/decline`);
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const startDM = async (userId: string) => {
    try {
      const data = await api.post('/api/dms', { recipient_id: userId });
      router.push(`/dm/${data.dm.dm_id}`);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const removeFriend = async (friendshipId: string) => {
    Alert.alert('Remove Friend', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => {
        try { await api.delete(`/api/friends/${friendshipId}`); loadData(); } catch {}
      }},
    ]);
  };

  if (loading) {
    return <SafeAreaView style={styles.safe}><View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="friends-back-btn" onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Friends</Text>
      </View>

      <View style={styles.tabs}>
        {(['friends', 'pending', 'add'] as Tab[]).map(t => (
          <TouchableOpacity key={t} testID={`tab-${t}`} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t === 'friends' ? `All (${friends.length})` : t === 'pending' ? `Pending (${incoming.length})` : 'Add Friend'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'friends' && (
        <FlatList
          data={friends}
          keyExtractor={(item) => item.friendship_id}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} tintColor={Colors.primary} />}
          ListEmptyComponent={<View style={styles.empty}><Ionicons name="people-outline" size={48} color={Colors.text_tertiary} /><Text style={styles.emptyText}>No friends yet</Text></View>}
          renderItem={({ item }) => (
            <View style={styles.friendRow}>
              <View style={styles.friendAvatar}><Text style={styles.friendAvatarText}>{item.username?.[0]?.toUpperCase()}</Text>
                <View style={[styles.onlineDot, { backgroundColor: item.is_online ? Colors.online : Colors.offline }]} />
              </View>
              <View style={styles.friendInfo}>
                <Text style={styles.friendName}>{item.display_name || item.username}</Text>
                <Text style={styles.friendUsername}>@{item.username}</Text>
              </View>
              <TouchableOpacity testID={`dm-friend-${item.user_id}`} style={styles.actionBtn} onPress={() => startDM(item.user_id)}>
                <Ionicons name="chatbubble-outline" size={18} color={Colors.primary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionBtn} onPress={() => removeFriend(item.friendship_id)}>
                <Ionicons name="close" size={18} color={Colors.text_tertiary} />
              </TouchableOpacity>
            </View>
          )}
        />
      )}

      {tab === 'pending' && (
        <FlatList
          data={incoming}
          keyExtractor={(item) => item.friendship_id}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<View style={styles.empty}><Ionicons name="time-outline" size={48} color={Colors.text_tertiary} /><Text style={styles.emptyText}>No pending requests</Text></View>}
          renderItem={({ item }) => (
            <View style={styles.friendRow}>
              <View style={styles.friendAvatar}><Text style={styles.friendAvatarText}>{item.from_user?.username?.[0]?.toUpperCase()}</Text></View>
              <View style={styles.friendInfo}>
                <Text style={styles.friendName}>{item.from_user?.display_name || item.from_user?.username}</Text>
                <Text style={styles.friendUsername}>Incoming request</Text>
              </View>
              <TouchableOpacity testID={`accept-${item.friendship_id}`} style={[styles.actionBtn, { backgroundColor: Colors.success + '20' }]} onPress={() => acceptRequest(item.friendship_id)}>
                <Ionicons name="checkmark" size={18} color={Colors.success} />
              </TouchableOpacity>
              <TouchableOpacity style={[styles.actionBtn, { backgroundColor: Colors.error + '20' }]} onPress={() => declineRequest(item.friendship_id)}>
                <Ionicons name="close" size={18} color={Colors.error} />
              </TouchableOpacity>
            </View>
          )}
        />
      )}

      {tab === 'add' && (
        <View style={styles.addSection}>
          <View style={styles.searchBar}>
            <Ionicons name="search" size={18} color={Colors.text_tertiary} />
            <TextInput testID="friend-search-input" style={styles.searchInput} value={searchQuery} onChangeText={setSearchQuery} placeholder="Search by username..." placeholderTextColor={Colors.text_tertiary} returnKeyType="search" onSubmitEditing={searchUsers} autoCapitalize="none" />
          </View>
          <FlatList
            data={searchResults}
            keyExtractor={(item) => item.user_id}
            contentContainerStyle={styles.list}
            renderItem={({ item }) => (
              <View style={styles.friendRow}>
                <View style={styles.friendAvatar}><Text style={styles.friendAvatarText}>{item.username?.[0]?.toUpperCase()}</Text></View>
                <View style={styles.friendInfo}>
                  <Text style={styles.friendName}>{item.display_name || item.username}</Text>
                  <Text style={styles.friendUsername}>@{item.username}</Text>
                </View>
                <TouchableOpacity testID={`add-friend-${item.user_id}`} style={[styles.actionBtn, { backgroundColor: Colors.primary + '20' }]} onPress={() => sendFriendRequest(item.user_id)}>
                  <Ionicons name="person-add" size={16} color={Colors.primary} />
                </TouchableOpacity>
              </View>
            )}
          />
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { fontSize: 20, fontWeight: '800', color: Colors.text_primary },
  tabs: { flexDirection: 'row', paddingHorizontal: 16, paddingTop: 12, gap: 8 },
  tab: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, backgroundColor: Colors.surface },
  tabActive: { backgroundColor: Colors.primary },
  tabText: { fontSize: 13, fontWeight: '600', color: Colors.text_secondary },
  tabTextActive: { color: '#FFF' },
  list: { padding: 16, gap: 4 },
  friendRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, paddingHorizontal: 4 },
  friendAvatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  friendAvatarText: { color: Colors.text_primary, fontSize: 18, fontWeight: '700' },
  onlineDot: { position: 'absolute', bottom: 0, right: 0, width: 12, height: 12, borderRadius: 6, borderWidth: 2, borderColor: Colors.bg_primary },
  friendInfo: { flex: 1 },
  friendName: { fontSize: 15, fontWeight: '600', color: Colors.text_primary },
  friendUsername: { fontSize: 12, color: Colors.text_tertiary },
  actionBtn: { width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.surface },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60, gap: 8 },
  emptyText: { color: Colors.text_secondary, fontSize: 14 },
  addSection: { flex: 1 },
  searchBar: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: Colors.bg_secondary, marginHorizontal: 16, marginTop: 12, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10, borderWidth: 1, borderColor: Colors.border },
  searchInput: { flex: 1, color: Colors.text_primary, fontSize: 15 },
});
