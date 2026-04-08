import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/AuthContext';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>({ servers: [], users: [], messages: [] });
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const { user } = useAuth();
  const router = useRouter();

  const handleSearch = async () => {
    if (!query.trim() || query.trim().length < 2) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.get(`/api/search?q=${encodeURIComponent(query.trim())}`);
      setResults(data);
    } catch (e) {
      console.error('Search error:', e);
    } finally {
      setLoading(false);
    }
  };

  const startDM = async (userId: string) => {
    try {
      const data = await api.post('/api/dms', { recipient_id: userId });
      router.push(`/dm/${data.dm.dm_id}`);
    } catch (e) {
      console.error('Failed to create DM:', e);
    }
  };

  const totalResults = results.servers.length + results.users.length + results.messages.length;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Search</Text>
      </View>
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color={Colors.text_tertiary} />
        <TextInput
          testID="search-input"
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder="Search servers, users, messages..."
          placeholderTextColor={Colors.text_tertiary}
          returnKeyType="search"
          onSubmitEditing={handleSearch}
          autoCapitalize="none"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => { setQuery(''); setResults({ servers: [], users: [], messages: [] }); setSearched(false); }}>
            <Ionicons name="close-circle" size={18} color={Colors.text_tertiary} />
          </TouchableOpacity>
        )}
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
      ) : searched && totalResults === 0 ? (
        <View style={styles.center}>
          <Ionicons name="search-outline" size={48} color={Colors.text_tertiary} />
          <Text style={styles.emptyText}>No results found</Text>
        </View>
      ) : (
        <FlatList
          data={[
            ...results.servers.map((s: any) => ({ ...s, _type: 'server' })),
            ...results.users.map((u: any) => ({ ...u, _type: 'user' })),
            ...results.messages.map((m: any) => ({ ...m, _type: 'message' })),
          ]}
          keyExtractor={(item, idx) => `${item._type}-${idx}`}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => {
            if (item._type === 'server') {
              return (
                <TouchableOpacity testID={`search-server-${item.server_id}`} style={styles.resultCard}>
                  <View style={[styles.resultIcon, { backgroundColor: Colors.primary }]}>
                    <Ionicons name="planet" size={18} color="#FFF" />
                  </View>
                  <View style={styles.resultInfo}>
                    <Text style={styles.resultLabel}>SERVER</Text>
                    <Text style={styles.resultName}>{item.name}</Text>
                  </View>
                </TouchableOpacity>
              );
            }
            if (item._type === 'user') {
              return (
                <TouchableOpacity
                  testID={`search-user-${item.user_id}`}
                  style={styles.resultCard}
                  onPress={() => startDM(item.user_id)}
                >
                  <View style={[styles.resultIcon, { backgroundColor: Colors.bg_tertiary }]}>
                    <Text style={styles.resultIconText}>{item.username?.[0]?.toUpperCase()}</Text>
                  </View>
                  <View style={styles.resultInfo}>
                    <Text style={styles.resultLabel}>USER</Text>
                    <Text style={styles.resultName}>{item.username}</Text>
                  </View>
                  <View style={[styles.statusDot, { backgroundColor: item.is_online ? Colors.online : Colors.offline }]} />
                </TouchableOpacity>
              );
            }
            return (
              <View style={styles.resultCard}>
                <View style={[styles.resultIcon, { backgroundColor: Colors.surface_hover }]}>
                  <Ionicons name="chatbubble" size={16} color={Colors.text_secondary} />
                </View>
                <View style={styles.resultInfo}>
                  <Text style={styles.resultLabel}>MESSAGE</Text>
                  <Text style={styles.resultName} numberOfLines={2}>{item.content}</Text>
                  <Text style={styles.resultMeta}>by {item.sender_username}</Text>
                </View>
              </View>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  header: {
    paddingHorizontal: 20, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { fontSize: 28, fontWeight: '900', color: Colors.text_primary },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: Colors.bg_secondary, margin: 16,
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10,
    borderWidth: 1, borderColor: Colors.border,
  },
  searchInput: { flex: 1, color: Colors.text_primary, fontSize: 15 },
  list: { padding: 16, gap: 8 },
  resultCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: Colors.surface, borderRadius: 10, padding: 12,
    borderWidth: 1, borderColor: Colors.border,
  },
  resultIcon: {
    width: 40, height: 40, borderRadius: 12,
    justifyContent: 'center', alignItems: 'center',
  },
  resultIconText: { color: Colors.text_primary, fontSize: 16, fontWeight: '700' },
  resultInfo: { flex: 1 },
  resultLabel: { fontSize: 9, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1 },
  resultName: { fontSize: 14, fontWeight: '600', color: Colors.text_primary, marginTop: 1 },
  resultMeta: { fontSize: 11, color: Colors.text_tertiary, marginTop: 2 },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  emptyText: { color: Colors.text_secondary, fontSize: 15 },
});
