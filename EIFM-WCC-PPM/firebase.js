import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCgbcK1uunx4FPtmS3uf3i_MyvmaDoDufg",
  authDomain: "eifm-wcc-ppm.firebaseapp.com",
  projectId: "eifm-wcc-ppm",
  storageBucket: "eifm-wcc-ppm.firebasestorage.app",
  messagingSenderId: "641028866264",
  appId: "1:641028866264:web:36ef50f9e3e231b09b17ad"
};

export const firebaseConfigured = !firebaseConfig.apiKey.startsWith("PASTE_");

export const auth = firebaseConfigured
  ? getAuth(initializeApp(firebaseConfig))
  : null;
