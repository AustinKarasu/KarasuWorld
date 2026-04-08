import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/AuthContext';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

export default function ProfileScreen() {
  const { user, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [username, setUsername] = useState(user?.username || '');
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/api/users/me', { username, bio });
      await refreshUser();
      setEditing(false);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: async () => {
        await logout();
        router.replace('/(auth)/login');
      }},
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile</Text>
        <TouchableOpacity testID="settings-btn" onPress={() => router.push('/settings')}>
          <Ionicons name="settings-outline" size={24} color={Colors.text_secondary} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.username?.[0]?.toUpperCase() || '?'}</Text>
          </View>
          <View style={styles.statusBadge}>
            <View style={[styles.statusDot, { backgroundColor: Colors.online }]} />
            <Text style={styles.statusText}>Online</Text>
          </View>
        </View>

        {editing ? (
          <View style={styles.editSection}>
            <Text style={styles.label}>USERNAME</Text>
            <TextInput
              testID="edit-username-input"
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholderTextColor={Colors.text_tertiary}
            />
            <Text style={styles.label}>BIO</Text>
            <TextInput
              testID="edit-bio-input"
              style={[styles.input, styles.bioInput]}
              value={bio}
              onChangeText={setBio}
              placeholder="Tell us about yourself..."
              placeholderTextColor={Colors.text_tertiary}
              multiline
            />
            <View style={styles.editActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => { setEditing(false); setUsername(user?.username || ''); setBio(user?.bio || ''); }}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="save-profile-btn" style={styles.saveBtn} onPress={handleSave} disabled={saving}>
                <Text style={styles.saveBtnText}>{saving ? 'Saving...' : 'Save'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.infoSection}>
            <View style={styles.infoRow}>
              <Text style={styles.label}>USERNAME</Text>
              <Text style={styles.infoValue}>{user?.username}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.label}>EMAIL</Text>
              <Text style={styles.infoValue}>{user?.email}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.label}>BIO</Text>
              <Text style={styles.infoValue}>{user?.bio || 'No bio set'}</Text>
            </View>
            <TouchableOpacity testID="edit-profile-btn" style={styles.editBtn} onPress={() => setEditing(true)}>
              <Ionicons name="pencil" size={16} color={Colors.primary} />
              <Text style={styles.editBtnText}>Edit Profile</Text>
            </TouchableOpacity>
          </View>
        )}

        <TouchableOpacity testID="logout-btn" style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color={Colors.error} />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { fontSize: 28, fontWeight: '900', color: Colors.text_primary },
  content: { padding: 20, gap: 24 },
  profileCard: { alignItems: 'center', paddingVertical: 24 },
  avatar: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center',
  },
  avatarText: { color: '#FFF', fontSize: 36, fontWeight: '800' },
  statusBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: Colors.surface, borderRadius: 16,
    paddingHorizontal: 12, paddingVertical: 6, marginTop: 12,
    borderWidth: 1, borderColor: Colors.border,
  },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12, color: Colors.text_secondary, fontWeight: '600' },
  infoSection: {
    backgroundColor: Colors.surface, borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: Colors.border, gap: 16,
  },
  infoRow: { gap: 4 },
  label: { fontSize: 10, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1, marginBottom: 4, marginTop: 8 },
  infoValue: { fontSize: 15, color: Colors.text_primary, fontWeight: '500' },
  editBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    paddingVertical: 10, marginTop: 4,
  },
  editBtnText: { color: Colors.primary, fontSize: 14, fontWeight: '700' },
  editSection: {
    backgroundColor: Colors.surface, borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: Colors.border,
  },
  input: {
    backgroundColor: Colors.bg_secondary, borderWidth: 1,
    borderColor: Colors.border, borderRadius: 8, padding: 12,
    color: Colors.text_primary, fontSize: 15,
  },
  bioInput: { minHeight: 80, textAlignVertical: 'top' },
  editActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  cancelBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 8,
    backgroundColor: Colors.surface_hover, alignItems: 'center',
  },
  cancelBtnText: { color: Colors.text_secondary, fontWeight: '700' },
  saveBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 8,
    backgroundColor: Colors.primary, alignItems: 'center',
  },
  saveBtnText: { color: '#FFF', fontWeight: '700' },
  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    paddingVertical: 14, borderRadius: 12,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
  },
  logoutText: { color: Colors.error, fontSize: 15, fontWeight: '700' },
});
