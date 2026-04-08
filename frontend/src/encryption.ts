import CryptoJS from 'crypto-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY_PREFIX = 'e2e_key_';

function deriveSharedKey(myId: string, otherId: string, dmId: string): string {
  const combined = [myId, otherId].sort().join(':') + ':' + dmId;
  return CryptoJS.SHA256(combined).toString();
}

export async function getOrCreateDMKey(dmId: string, myId: string, otherId: string): Promise<string> {
  const stored = await AsyncStorage.getItem(`${KEY_PREFIX}${dmId}`);
  if (stored) return stored;
  const key = deriveSharedKey(myId, otherId, dmId);
  await AsyncStorage.setItem(`${KEY_PREFIX}${dmId}`, key);
  return key;
}

export function encryptMessage(message: string, key: string): string {
  return CryptoJS.AES.encrypt(message, key).toString();
}

export function decryptMessage(ciphertext: string, key: string): string {
  try {
    const bytes = CryptoJS.AES.decrypt(ciphertext, key);
    const decrypted = bytes.toString(CryptoJS.enc.Utf8);
    return decrypted || ciphertext;
  } catch {
    return ciphertext;
  }
}
