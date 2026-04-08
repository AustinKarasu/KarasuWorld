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

export default function CreateServerScreen() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleCreate = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Server name is required');
      return;
    }
    setLoading(true);
    try {
      const data = await api.post('/api/servers', { name: name.trim(), description: description.trim() });
      router.back();
      setTimeout(() => router.push(`/server/${data.server.server_id}`), 100);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to create server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <View style={styles.header}>
          <TouchableOpacity testID="close-btn" onPress={() => router.back()} style={styles.closeBtn}>
            <Ionicons name="close" size={24} color={Colors.text_secondary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Create Server</Text>
          <View style={{ width: 32 }} />
        </View>

        <View style={styles.content}>
          <View style={styles.iconPreview}>
            <Text style={styles.iconText}>{name?.[0]?.toUpperCase() || '?'}</Text>
          </View>

          <Text style={styles.label}>SERVER NAME</Text>
          <TextInput
            testID="server-name-input"
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Enter server name"
            placeholderTextColor={Colors.text_tertiary}
            autoFocus
            maxLength={50}
          />

          <Text style={styles.label}>DESCRIPTION</Text>
          <TextInput
            testID="server-description-input"
            style={[styles.input, styles.descInput]}
            value={description}
            onChangeText={setDescription}
            placeholder="What's this server about?"
            placeholderTextColor={Colors.text_tertiary}
            multiline
            maxLength={200}
          />

          <TouchableOpacity
            testID="create-server-submit-btn"
            style={[styles.createBtn, loading && styles.createBtnDisabled]}
            onPress={handleCreate}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" size="small" />
            ) : (
              <Text style={styles.createBtnText}>Create Server</Text>
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
  content: { padding: 24, gap: 4 },
  iconPreview: {
    width: 72, height: 72, borderRadius: 20,
    backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center',
    alignSelf: 'center', marginBottom: 24,
  },
  iconText: { color: '#FFF', fontSize: 28, fontWeight: '800' },
  label: {
    fontSize: 11, fontWeight: '700', color: Colors.text_secondary,
    letterSpacing: 1, marginTop: 16, marginBottom: 6,
  },
  input: {
    backgroundColor: Colors.bg_secondary, borderWidth: 1,
    borderColor: Colors.border, borderRadius: 8, padding: 14,
    color: Colors.text_primary, fontSize: 15,
  },
  descInput: { minHeight: 80, textAlignVertical: 'top' },
  createBtn: {
    backgroundColor: Colors.primary, borderRadius: 8,
    padding: 16, alignItems: 'center', marginTop: 24,
  },
  createBtnDisabled: { opacity: 0.6 },
  createBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
