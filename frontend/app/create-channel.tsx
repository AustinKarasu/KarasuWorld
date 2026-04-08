import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

export default function CreateChannelScreen() {
  const { serverId, type } = useLocalSearchParams<{ serverId: string; type: string }>();
  const [name, setName] = useState('');
  const [channelType, setChannelType] = useState(type || 'text');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleCreate = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Channel name is required');
      return;
    }
    setLoading(true);
    try {
      await api.post(`/api/servers/${serverId}/channels`, {
        name: name.trim(),
        channel_type: channelType,
      });
      router.back();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to create channel');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <View style={styles.header}>
          <TouchableOpacity testID="close-channel-btn" onPress={() => router.back()} style={styles.closeBtn}>
            <Ionicons name="close" size={24} color={Colors.text_secondary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Create Channel</Text>
          <View style={{ width: 32 }} />
        </View>

        <View style={styles.content}>
          <Text style={styles.label}>CHANNEL TYPE</Text>
          <View style={styles.typeRow}>
            <TouchableOpacity
              testID="type-text-btn"
              style={[styles.typeBtn, channelType === 'text' && styles.typeBtnActive]}
              onPress={() => setChannelType('text')}
            >
              <Ionicons name="chatbox-outline" size={20} color={channelType === 'text' ? '#FFF' : Colors.text_secondary} />
              <Text style={[styles.typeBtnText, channelType === 'text' && styles.typeBtnTextActive]}>Text</Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="type-voice-btn"
              style={[styles.typeBtn, channelType === 'voice' && styles.typeBtnActive]}
              onPress={() => setChannelType('voice')}
            >
              <Ionicons name="volume-high-outline" size={20} color={channelType === 'voice' ? '#FFF' : Colors.text_secondary} />
              <Text style={[styles.typeBtnText, channelType === 'voice' && styles.typeBtnTextActive]}>Voice</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>CHANNEL NAME</Text>
          <TextInput
            testID="channel-name-input"
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="new-channel"
            placeholderTextColor={Colors.text_tertiary}
            autoFocus
            autoCapitalize="none"
            maxLength={50}
          />

          <TouchableOpacity
            testID="create-channel-submit-btn"
            style={[styles.createBtn, loading && styles.createBtnDisabled]}
            onPress={handleCreate}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" size="small" />
            ) : (
              <Text style={styles.createBtnText}>Create Channel</Text>
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
  content: { padding: 24 },
  label: {
    fontSize: 11, fontWeight: '700', color: Colors.text_secondary,
    letterSpacing: 1, marginBottom: 8, marginTop: 16,
  },
  typeRow: { flexDirection: 'row', gap: 12 },
  typeBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, paddingVertical: 12, borderRadius: 8,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
  },
  typeBtnActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  typeBtnText: { color: Colors.text_secondary, fontWeight: '600' },
  typeBtnTextActive: { color: '#FFF' },
  input: {
    backgroundColor: Colors.bg_secondary, borderWidth: 1,
    borderColor: Colors.border, borderRadius: 8, padding: 14,
    color: Colors.text_primary, fontSize: 15,
  },
  createBtn: {
    backgroundColor: Colors.primary, borderRadius: 8,
    padding: 16, alignItems: 'center', marginTop: 24,
  },
  createBtnDisabled: { opacity: 0.6 },
  createBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
