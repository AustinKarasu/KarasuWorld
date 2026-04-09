import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, TextInput, Alert, ScrollView, Image,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { api } from '@/src/api';
import { Colors } from '@/src/colors';

const ROLE_COLORS = ['#E74C3C', '#E67E22', '#F1C40F', '#2ECC71', '#3498DB', '#9B59B6', '#E91E63', '#00BCD4', '#99AAB5'];
const PERMISSION_LIST = [
  { key: 'administrator', label: 'Administrator', desc: 'Full access', bit: 1 << 0 },
  { key: 'manage_server', label: 'Manage Server', desc: 'Edit server settings', bit: 1 << 1 },
  { key: 'manage_channels', label: 'Manage Channels', desc: 'Create/edit/delete channels', bit: 1 << 2 },
  { key: 'manage_roles', label: 'Manage Roles', desc: 'Create/edit/delete roles', bit: 1 << 3 },
  { key: 'manage_members', label: 'Manage Members', desc: 'Edit member roles', bit: 1 << 4 },
  { key: 'kick_members', label: 'Kick Members', desc: 'Remove members', bit: 1 << 5 },
  { key: 'ban_members', label: 'Ban Members', desc: 'Ban members', bit: 1 << 6 },
  { key: 'send_messages', label: 'Send Messages', desc: 'Send messages in text channels', bit: 1 << 7 },
  { key: 'manage_messages', label: 'Manage Messages', desc: 'Delete others messages', bit: 1 << 8 },
  { key: 'add_reactions', label: 'Add Reactions', desc: 'React to messages', bit: 1 << 9 },
  { key: 'connect_voice', label: 'Connect Voice', desc: 'Join voice channels', bit: 1 << 10 },
  { key: 'speak', label: 'Speak', desc: 'Talk in voice channels', bit: 1 << 11 },
  { key: 'attach_files', label: 'Attach Files', desc: 'Upload images and files', bit: 1 << 15 },
  { key: 'view_channels', label: 'View Channels', desc: 'See channels', bit: 1 << 16 },
];

export default function ServerSettingsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [serverName, setServerName] = useState('');
  const [serverDescription, setServerDescription] = useState('');
  const [serverIconBase64, setServerIconBase64] = useState('');
  const [serverBannerBase64, setServerBannerBase64] = useState('');
  const [roles, setRoles] = useState<any[]>([]);
  const [members, setMembers] = useState<any[]>([]);
  const [selectedRole, setSelectedRole] = useState<any>(null);
  const [newRoleName, setNewRoleName] = useState('');
  const [editPerms, setEditPerms] = useState(0);
  const [editColor, setEditColor] = useState('#99AAB5');
  const [tab, setTab] = useState<'roles' | 'members'>('roles');
  const router = useRouter();

  useEffect(() => { loadData(); }, [id]);

  const loadData = async () => {
    try {
      const [serverData, rolesData, membersData] = await Promise.all([
        api.get(`/api/servers/${id}`),
        api.get(`/api/servers/${id}/roles`),
        api.get(`/api/servers/${id}/members`),
      ]);
      const server = serverData.server || {};
      setServerName(server.name || '');
      setServerDescription(server.description || '');
      setServerIconBase64(server.icon_base64 || '');
      setServerBannerBase64(server.banner_base64 || '');
      setRoles(rolesData.roles || []);
      setMembers(membersData.members || []);
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const pickServerImage = async (type: 'icon' | 'banner') => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission required', 'Please allow media library access.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.75,
      base64: true,
    });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    if (!asset.base64) return;
    const mime = asset.mimeType || 'image/jpeg';
    const dataUri = `data:${mime};base64,${asset.base64}`;
    if (type === 'icon') {
      setServerIconBase64(dataUri);
    } else {
      setServerBannerBase64(dataUri);
    }
  };

  const saveServerSettings = async () => {
    try {
      await api.put(`/api/servers/${id}`, {
        name: serverName.trim(),
        description: serverDescription,
        icon_base64: serverIconBase64,
        banner_base64: serverBannerBase64,
      });
      Alert.alert('Saved', 'Server settings updated successfully.');
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const createRole = async () => {
    if (!newRoleName.trim()) return;
    try {
      await api.post(`/api/servers/${id}/roles`, { name: newRoleName.trim(), color: editColor, permissions: editPerms });
      setNewRoleName('');
      setEditPerms(0);
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const updateRole = async () => {
    if (!selectedRole) return;
    try {
      await api.put(`/api/servers/${id}/roles/${selectedRole.role_id}`, {
        name: selectedRole.name, color: editColor, permissions: editPerms,
      });
      setSelectedRole(null);
      loadData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };

  const deleteRole = async (roleId: string) => {
    Alert.alert('Delete Role', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try { await api.delete(`/api/servers/${id}/roles/${roleId}`); loadData(); } catch (e: any) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  const togglePerm = (bit: number) => setEditPerms(prev => prev ^ bit);

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><Ionicons name="chevron-back" size={24} color={Colors.text_primary} /></TouchableOpacity>
        <Text style={styles.headerTitle}>Server Settings</Text>
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity style={[styles.tab, tab === 'roles' && styles.tabActive]} onPress={() => setTab('roles')}>
          <Text style={[styles.tabText, tab === 'roles' && styles.tabTextActive]}>Roles ({roles.length})</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, tab === 'members' && styles.tabActive]} onPress={() => setTab('members')}>
          <Text style={[styles.tabText, tab === 'members' && styles.tabTextActive]}>Members ({members.length})</Text>
        </TouchableOpacity>
      </View>

      {tab === 'roles' ? (
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>SERVER PROFILE</Text>
            <TouchableOpacity style={styles.serverBannerPicker} onPress={() => pickServerImage('banner')}>
              {serverBannerBase64 ? (
                <Image source={{ uri: serverBannerBase64 }} style={styles.serverBannerImage} />
              ) : (
                <View style={styles.serverBannerPlaceholder}>
                  <Ionicons name="image-outline" size={22} color={Colors.text_tertiary} />
                  <Text style={styles.serverBannerText}>Tap to upload server banner</Text>
                </View>
              )}
            </TouchableOpacity>
            <View style={styles.serverIconRow}>
              <TouchableOpacity style={styles.serverIconPicker} onPress={() => pickServerImage('icon')}>
                {serverIconBase64 ? (
                  <Image source={{ uri: serverIconBase64 }} style={styles.serverIconImage} />
                ) : (
                  <Text style={styles.serverIconText}>{serverName?.[0]?.toUpperCase() || 'S'}</Text>
                )}
              </TouchableOpacity>
              <View style={{ flex: 1, gap: 8 }}>
                <TextInput style={styles.input} value={serverName} onChangeText={setServerName} placeholder="Server name" placeholderTextColor={Colors.text_tertiary} />
                <TextInput
                  style={[styles.input, styles.multilineInput]}
                  value={serverDescription}
                  onChangeText={setServerDescription}
                  placeholder="Server description"
                  placeholderTextColor={Colors.text_tertiary}
                  multiline
                />
              </View>
            </View>
            <TouchableOpacity style={styles.createBtn} onPress={saveServerSettings}>
              <Text style={styles.createBtnText}>Save Server Profile</Text>
            </TouchableOpacity>
          </View>

          {/* Create New Role */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>CREATE NEW ROLE</Text>
            <TextInput testID="new-role-name" style={styles.input} value={newRoleName} onChangeText={setNewRoleName} placeholder="Role name" placeholderTextColor={Colors.text_tertiary} />
            <View style={styles.colorRow}>
              {ROLE_COLORS.map(c => (
                <TouchableOpacity key={c} style={[styles.colorDot, { backgroundColor: c }, editColor === c && styles.colorDotActive]} onPress={() => setEditColor(c)} />
              ))}
            </View>
            <TouchableOpacity testID="create-role-btn" style={styles.createBtn} onPress={createRole}><Text style={styles.createBtnText}>Create Role</Text></TouchableOpacity>
          </View>

          {/* Existing Roles */}
          <Text style={styles.sectionTitle}>EXISTING ROLES</Text>
          {roles.map(role => (
            <TouchableOpacity key={role.role_id} style={styles.roleCard} onPress={() => { setSelectedRole(role); setEditPerms(role.permissions); setEditColor(role.color); }}>
              <View style={[styles.roleColor, { backgroundColor: role.color }]} />
              <View style={styles.roleInfo}>
                <Text style={styles.roleName}>{role.name}</Text>
                <Text style={styles.rolePerms}>{role.is_default ? 'Default' : 'Custom'}</Text>
              </View>
              {!role.is_default && (
                <TouchableOpacity onPress={() => deleteRole(role.role_id)}><Ionicons name="trash-outline" size={18} color={Colors.error} /></TouchableOpacity>
              )}
            </TouchableOpacity>
          ))}

          {/* Edit Role Permissions */}
          {selectedRole && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>EDIT: {selectedRole.name}</Text>
              {PERMISSION_LIST.map(p => (
                <TouchableOpacity key={p.key} style={styles.permRow} onPress={() => togglePerm(p.bit)}>
                  <View style={[styles.checkbox, (editPerms & p.bit) !== 0 && styles.checkboxActive]}>
                    {(editPerms & p.bit) !== 0 && <Ionicons name="checkmark" size={14} color="#FFF" />}
                  </View>
                  <View style={styles.permInfo}>
                    <Text style={styles.permLabel}>{p.label}</Text>
                    <Text style={styles.permDesc}>{p.desc}</Text>
                  </View>
                </TouchableOpacity>
              ))}
              <TouchableOpacity testID="save-role-btn" style={styles.saveBtn} onPress={updateRole}><Text style={styles.saveBtnText}>Save Permissions</Text></TouchableOpacity>
            </View>
          )}
        </ScrollView>
      ) : (
        <FlatList
          data={members}
          keyExtractor={(item) => item.user_id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <View style={styles.memberRow}>
              <View style={styles.memberAvatar}><Text style={styles.memberAvatarText}>{item.username?.[0]?.toUpperCase()}</Text></View>
              <View style={styles.memberInfo}>
                <Text style={styles.memberName}>{item.display_name || item.username}</Text>
                <Text style={styles.memberRole}>{item.role}</Text>
              </View>
              <View style={[styles.memberStatus, { backgroundColor: item.is_online ? Colors.online : Colors.offline }]} />
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { fontSize: 20, fontWeight: '800', color: Colors.text_primary },
  tabs: { flexDirection: 'row', paddingHorizontal: 16, paddingTop: 12, gap: 8 },
  tab: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, backgroundColor: Colors.surface },
  tabActive: { backgroundColor: Colors.primary },
  tabText: { fontSize: 13, fontWeight: '600', color: Colors.text_secondary },
  tabTextActive: { color: '#FFF' },
  content: { padding: 16, gap: 12 },
  list: { padding: 16, gap: 4 },
  section: { backgroundColor: Colors.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: Colors.border, gap: 8 },
  sectionTitle: { fontSize: 11, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1, marginTop: 8, marginBottom: 4 },
  input: { backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, borderRadius: 8, padding: 12, color: Colors.text_primary, fontSize: 15 },
  multilineInput: { minHeight: 74, textAlignVertical: 'top' },
  serverBannerPicker: { width: '100%', height: 120, borderRadius: 10, backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, overflow: 'hidden' },
  serverBannerImage: { width: '100%', height: '100%' },
  serverBannerPlaceholder: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 6 },
  serverBannerText: { fontSize: 12, color: Colors.text_tertiary },
  serverIconRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  serverIconPicker: { width: 72, height: 72, borderRadius: 16, backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, justifyContent: 'center', alignItems: 'center', overflow: 'hidden' },
  serverIconImage: { width: '100%', height: '100%' },
  serverIconText: { color: Colors.text_primary, fontSize: 28, fontWeight: '700' },
  colorRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  colorDot: { width: 28, height: 28, borderRadius: 14 },
  colorDotActive: { borderWidth: 3, borderColor: '#FFF' },
  createBtn: { backgroundColor: Colors.primary, borderRadius: 8, padding: 12, alignItems: 'center' },
  createBtnText: { color: '#FFF', fontWeight: '700' },
  roleCard: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: Colors.surface, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: Colors.border },
  roleColor: { width: 16, height: 16, borderRadius: 8 },
  roleInfo: { flex: 1 },
  roleName: { fontSize: 15, fontWeight: '600', color: Colors.text_primary },
  rolePerms: { fontSize: 11, color: Colors.text_tertiary },
  permRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8 },
  checkbox: { width: 22, height: 22, borderRadius: 4, borderWidth: 2, borderColor: Colors.text_tertiary, justifyContent: 'center', alignItems: 'center' },
  checkboxActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  permInfo: { flex: 1 },
  permLabel: { fontSize: 14, fontWeight: '600', color: Colors.text_primary },
  permDesc: { fontSize: 11, color: Colors.text_tertiary },
  saveBtn: { backgroundColor: Colors.success, borderRadius: 8, padding: 12, alignItems: 'center', marginTop: 8 },
  saveBtnText: { color: '#FFF', fontWeight: '700' },
  memberRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8, paddingHorizontal: 4 },
  memberAvatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center' },
  memberAvatarText: { color: Colors.text_primary, fontSize: 16, fontWeight: '700' },
  memberInfo: { flex: 1 },
  memberName: { fontSize: 14, fontWeight: '600', color: Colors.text_primary },
  memberRole: { fontSize: 11, color: Colors.text_tertiary, textTransform: 'capitalize' },
  memberStatus: { width: 10, height: 10, borderRadius: 5 },
});
