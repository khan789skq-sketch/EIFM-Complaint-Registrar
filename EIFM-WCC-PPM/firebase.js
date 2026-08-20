import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
const firebaseConfig={
  apiKey:"PASTE_API_KEY",authDomain:"PASTE_PROJECT.firebaseapp.com",
  projectId:"PASTE_PROJECT_ID",storageBucket:"PASTE_PROJECT.firebasestorage.app",
  messagingSenderId:"PASTE_SENDER_ID",appId:"PASTE_APP_ID"
};
export const firebaseConfigured=!firebaseConfig.apiKey.startsWith("PASTE_");
export const auth=firebaseConfigured?getAuth(initializeApp(firebaseConfig)):null;