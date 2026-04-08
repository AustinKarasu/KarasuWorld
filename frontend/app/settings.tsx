import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/AuthContext';
import { Colors } from '@/src/colors';

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: async () => {
        await logout();
        router.replace('/(auth)/login');
      }},
    ]);
  };

  const settingsGroups = [
    {
      title: 'ACCOUNT',
      items: [
        { icon: 'person-outline' as const, label: 'Edit Profile', onPress: () => router.back() },
        { icon: 'lock-closed-outline' as const, label: 'Privacy & Security', onPress: () => {} },
      ],
    },
    {
      title: 'NOTIFICATIONS',
      items: [
        { icon: 'notifications-outline' as const, label: 'Push Notifications', onPress: () => {} },
        { icon: 'volume-medium-outline' as const, label: 'Sound & Vibration', onPress: () => {} },
      ],
    },
    {
      title: 'APP',
      items: [
        { icon: 'color-palette-outline' as const, label: 'Appearance', onPress: () => {} },
        { icon: 'language-outline' as const, label: 'Language', onPress: () => {} },
        { icon: 'information-circle-outline' as const, label: 'About KarasuWorld', onPress: () => {} },
      ],
    },
  ];

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="settings-back-btn" onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={Colors.text_primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {settingsGroups.map((group, gi) => (
          <View key={gi} style={styles.group}>
            <Text style={styles.groupTitle}>{group.title}</Text>
            <View style={styles.groupCard}>
              {group.items.map((item, ii) => (
                <TouchableOpacity
                  key={ii}
                  testID={`setting-${item.label.toLowerCase().replace(/\s/g, '-')}`}
                  style={[styles.settingRow, ii < group.items.length - 1 && styles.settingRowBorder]}
                  onPress={item.onPress}
                >
                  <Ionicons name={item.icon} size={20} color={Colors.text_secondary} />
                  <Text style={styles.settingLabel}>{item.label}</Text>
                  <Ionicons name="chevron-forward" size={18} color={Colors.text_tertiary} />
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ))}

        <TouchableOpacity testID="settings-logout-btn" style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color={Colors.error} />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <Text style={styles.version}>KarasuWorld v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingHorizontal: 12, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  backBtn: { padding: 4 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: Colors.text_primary },
  content: { padding: 16, gap: 24, paddingBottom: 40 },
  group: { gap: 8 },
  groupTitle: { fontSize: 11, fontWeight: '700', color: Colors.text_tertiary, letterSpacing: 1, paddingLeft: 4 },
  groupCard: {
    backgroundColor: Colors.surface, borderRadius: 12,
    borderWidth: 1, borderColor: Colors.border, overflow: 'hidden',
  },
  settingRow: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingVertical: 14, paddingHorizontal: 16,
  },
  settingRowBorder: { borderBottomWidth: 1, borderBottomColor: Colors.border },
  settingLabel: { flex: 1, fontSize: 15, color: Colors.text_primary, fontWeight: '500' },
  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    paddingVertical: 14, borderRadius: 12,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
  },
  logoutText: { color: Colors.error, fontSize: 15, fontWeight: '700' },
  version: { textAlign: 'center', fontSize: 12, color: Colors.text_tertiary },
});
