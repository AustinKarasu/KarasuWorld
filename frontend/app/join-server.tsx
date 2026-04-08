import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

export default function JoinServerScreen() {
  const [inviteCode, setInviteCode] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleJoin = async () => {
    if (!inviteCode.trim()) {
      Alert.alert('Error', 'Please enter an invite code');
      return;
    }
    setLoading(true);
    try {
      const data = await api.post('/api/servers/join', { invite_code: inviteCode.trim() });
      router.back();
      setTimeout(() => router.push(`/server/${data.server.server_id}`), 100);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to join server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <View style={styles.header}>
          <TouchableOpacity testID="close-join-btn" onPress={() => router.back()} style={styles.closeBtn}>
            <Ionicons name="close" size={24} color={Colors.text_secondary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Join Server</Text>
          <View style={{ width: 32 }} />
        </View>

        <View style={styles.content}>
          <Ionicons name="enter-outline" size={64} color={Colors.primary} style={styles.icon} />
          <Text style={styles.title}>Join a Server</Text>
          <Text style={styles.subtitle}>Enter an invite code to join an existing server</Text>

          <Text style={styles.label}>INVITE CODE</Text>
          <TextInput
            testID="invite-code-input"
            style={styles.input}
            value={inviteCode}
            onChangeText={setInviteCode}
            placeholder="Enter invite code"
            placeholderTextColor={Colors.text_tertiary}
            autoFocus
            autoCapitalize="none"
          />

          <TouchableOpacity
            testID="join-server-submit-btn"
            style={[styles.joinBtn, loading && styles.joinBtnDisabled]}
            onPress={handleJoin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" size="small" />
            ) : (
              <Text style={styles.joinBtnText}>Join Server</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  flex: { flex: 1 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  closeBtn: { padding: 4 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: Colors.text_primary },
  content: { padding: 24, alignItems: 'center' },
  icon: { marginBottom: 16 },
  title: { fontSize: 22, fontWeight: '800', color: Colors.text_primary },
  subtitle: { fontSize: 14, color: Colors.text_secondary, textAlign: 'center', marginTop: 8, marginBottom: 32 },
  label: {
    fontSize: 11, fontWeight: '700', color: Colors.text_secondary,
    letterSpacing: 1, marginBottom: 6, alignSelf: 'flex-start',
  },
  input: {
    backgroundColor: Colors.bg_secondary, borderWidth: 1,
    borderColor: Colors.border, borderRadius: 8, padding: 14,
    color: Colors.text_primary, fontSize: 15, width: '100%',
  },
  joinBtn: {
    backgroundColor: Colors.primary, borderRadius: 8,
    padding: 16, alignItems: 'center', marginTop: 24, width: '100%',
  },
  joinBtnDisabled: { opacity: 0.6 },
  joinBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
