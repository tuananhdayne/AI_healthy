import { initializeApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';

export const firebaseConfig = {
  apiKey: 'AIzaSyDQYrpwAvZM4jybGKF8U1iRXwkrv8pg-Vo',
  authDomain: 'giadienweb.firebaseapp.com',
  projectId: 'giadienweb',
  storageBucket: 'giadienweb.firebasestorage.app',
  messagingSenderId: '814944757194',
  appId: '1:814944757194:web:fbb1510849054c23301b33',
  measurementId: 'G-CJVC3QY2E8'
};

// Initialize Firebase
export const firebaseApp = initializeApp(firebaseConfig);
export const firebaseAuth: Auth = getAuth(firebaseApp);
export const firebaseDb: Firestore = getFirestore(firebaseApp);
