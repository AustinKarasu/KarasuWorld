import React, { useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert, Image,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '@/src/AuthContext';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

export default function ProfileScreen() {
  const { user, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [username, setUsername] = useState(user?.username || '');
  const [displayName, setDisplayName] = useState((user as any)?.display_name || '');
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);
  const [friendCount, setFriendCount] = useState(0);

  useFocusEffect(useCallback(() => {
    loadFriendCount();
  }, []));

  const loadFriendCount = async () => {
    try {
      const data = await api.get('/api/friends');
      setFriendCount(data.friends?.length || 0);
    } catch {}
  };

  const pickImage = async (type: 'avatar' | 'banner') => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.5,
      base64: true,
      allowsEditing: true,
      aspect: type === 'avatar' ? [1, 1] : [3, 1],
    });
    if (!result.canceled && result.assets[0].base64) {
      try {
        const field = type === 'avatar' ? 'avatar_base64' : 'banner_base64';
        await api.put('/api/users/me', { [field]: `data:image/jpeg;base64,${result.assets[0].base64}` });
        await refreshUser();
      } catch (e: any) {
        Alert.alert('Error', e.message);
      }
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/api/users/me', { username, bio, display_name: displayName });
      await refreshUser();
      setEditing(false);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: async () => { await logout(); router.replace('/(auth)/login'); }},
    ]);
  };

  const avatar = (user as any)?.avatar_base64;
  const banner = (user as any)?.banner_base64;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile</Text>
        <TouchableOpacity testID="settings-btn" onPress={() => router.push('/settings')}>
          <Ionicons name="settings-outline" size={24} color={Colors.text_secondary} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Banner */}
        <TouchableOpacity testID="edit-banner-btn" onPress={() => pickImage('banner')} style={styles.bannerContainer}>
          {banner ? (
            <Image source={{ uri: banner }} style={styles.banner} />
          ) : (
            <View style={styles.bannerPlaceholder}>
              <Ionicons name="image-outline" size={24} color={Colors.text_tertiary} />
              <Text style={styles.bannerText}>Tap to add banner</Text>
            </View>
          )}
        </TouchableOpacity>

        {/* Avatar */}
        <TouchableOpacity testID="edit-avatar-btn" onPress={() => pickImage('avatar')} style={styles.avatarContainer}>
          {avatar ? (
            <Image source={{ uri: avatar }} style={styles.avatar} />
          ) : (
            <View style={styles.avatarPlaceholder}>
              <Text style={styles.avatarText}>{user?.username?.[0]?.toUpperCase() || '?'}</Text>
            </View>
          )}
          <View style={styles.avatarEditBadge}>
            <Ionicons name="camera" size={14} color="#FFF" />
          </View>
        </TouchableOpacity>

        {/* Stats */}
        <View style={styles.statsRow}>
          <TouchableOpacity testID="friends-btn" style={styles.statItem} onPress={() => router.push('/friends')}>
            <Text style={styles.statValue}>{friendCount}</Text>
            <Text style={styles.statLabel}>Friends</Text>
          </TouchableOpacity>
          <View style={[styles.statusBadge, { backgroundColor: Colors.online + '20' }]}>
            <View style={[styles.statusDot, { backgroundColor: Colors.online }]} />
            <Text style={styles.statusText}>Online</Text>
          </View>
        </View>

        {editing ? (
          <View style={styles.editSection}>
            <Text style={styles.label}>DISPLAY NAME</Text>
            <TextInput testID="edit-display-name-input" style={styles.input} value={displayName} onChangeText={setDisplayName} placeholderTextColor={Colors.text_tertiary} />
            <Text style={styles.label}>USERNAME</Text>
            <TextInput testID="edit-username-input" style={styles.input} value={username} onChangeText={setUsername} placeholderTextColor={Colors.text_tertiary} />
            <Text style={styles.label}>ABOUT ME</Text>
            <TextInput testID="edit-bio-input" style={[styles.input, styles.bioInput]} value={bio} onChangeText={setBio} placeholder="Tell us about yourself..." placeholderTextColor={Colors.text_tertiary} multiline />
            <View style={styles.editActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setEditing(false)}><Text style={styles.cancelBtnText}>Cancel</Text></TouchableOpacity>
              <TouchableOpacity testID="save-profile-btn" style={styles.saveBtn} onPress={handleSave}><Text style={styles.saveBtnText}>{saving ? 'Saving...' : 'Save'}</Text></TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.infoSection}>
            <View style={styles.infoRow}><Text style={styles.label}>DISPLAY NAME</Text><Text style={styles.infoValue}>{(user as any)?.display_name || user?.username}</Text></View>
            <View style={styles.infoRow}><Text style={styles.label}>USERNAME</Text><Text style={styles.infoValue}>{user?.username}</Text></View>
            <View style={styles.infoRow}><Text style={styles.label}>EMAIL</Text><Text style={styles.infoValue}>{user?.email}</Text></View>
            <View style={styles.infoRow}><Text style={styles.label}>ABOUT ME</Text><Text style={styles.infoValue}>{user?.bio || 'No bio set'}</Text></View>
            <TouchableOpacity testID="edit-profile-btn" style={styles.editBtn} onPress={() => { setEditing(true); setUsername(user?.username || ''); setBio(user?.bio || ''); setDisplayName((user as any)?.display_name || ''); }}>
              <Ionicons name="pencil" size={16} color={Colors.primary} /><Text style={styles.editBtnText}>Edit Profile</Text>
            </TouchableOpacity>
          </View>
        )}

        <TouchableOpacity testID="logout-btn" style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color={Colors.error} /><Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { fontSize: 28, fontWeight: '900', color: Colors.text_primary },
  content: { paddingBottom: 40 },
  bannerContainer: { height: 120, backgroundColor: Colors.bg_tertiary },
  banner: { width: '100%', height: '100%' },
  bannerPlaceholder: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 4 },
  bannerText: { color: Colors.text_tertiary, fontSize: 12 },
  avatarContainer: { alignSelf: 'center', marginTop: -40, zIndex: 10 },
  avatar: { width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: Colors.bg_primary },
  avatarPlaceholder: { width: 80, height: 80, borderRadius: 40, backgroundColor: Colors.primary, justifyContent: 'center', alignItems: 'center', borderWidth: 4, borderColor: Colors.bg_primary },
  avatarText: { color: '#FFF', fontSize: 28, fontWeight: '800' },
  avatarEditBadge: { position: 'absolute', bottom: 0, right: 0, width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: Colors.bg_primary },
  statsRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 16, marginTop: 12, marginBottom: 16 },
  statItem: { alignItems: 'center' },
  statValue: { fontSize: 18, fontWeight: '800', color: Colors.text_primary },
  statLabel: { fontSize: 11, color: Colors.text_secondary },
  statusBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: 16, paddingHorizontal: 12, paddingVertical: 6 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12, color: Colors.text_secondary, fontWeight: '600' },
  infoSection: { backgroundColor: Colors.surface, borderRadius: 12, padding: 16, marginHorizontal: 16, borderWidth: 1, borderColor: Colors.border, gap: 12 },
  infoRow: { gap: 2 },
  label: { fontSize: 10, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1, marginBottom: 4, marginTop: 8 },
  infoValue: { fontSize: 15, color: Colors.text_primary, fontWeight: '500' },
  editBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 10, marginTop: 4 },
  editBtnText: { color: Colors.primary, fontSize: 14, fontWeight: '700' },
  editSection: { backgroundColor: Colors.surface, borderRadius: 12, padding: 16, marginHorizontal: 16, borderWidth: 1, borderColor: Colors.border },
  input: { backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, borderRadius: 8, padding: 12, color: Colors.text_primary, fontSize: 15 },
  bioInput: { minHeight: 80, textAlignVertical: 'top' },
  editActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  cancelBtn: { flex: 1, paddingVertical: 12, borderRadius: 8, backgroundColor: Colors.surface_hover, alignItems: 'center' },
  cancelBtnText: { color: Colors.text_secondary, fontWeight: '700' },
  saveBtn: { flex: 1, paddingVertical: 12, borderRadius: 8, backgroundColor: Colors.primary, alignItems: 'center' },
  saveBtnText: { color: '#FFF', fontWeight: '700' },
  logoutBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 12, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, marginHorizontal: 16, marginTop: 24 },
  logoutText: { color: Colors.error, fontSize: 15, fontWeight: '700' },
});
