import { createContext, useContext, useState } from 'react';

export type AuthState = {
  token: string | null;
  username: string | null;
  setSession: (token: string, username: string) => void;
  clear: () => void;
};

export const AuthContext = createContext<AuthState>({
  token: null,
  username: null,
  setSession: () => {},
  clear: () => {},
});

export const useAuthState = (): AuthState => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem('username'));
  return {
    token,
    username,
    setSession: (t, u) => {
      localStorage.setItem('token', t);
      localStorage.setItem('username', u);
      setToken(t);
      setUsername(u);
    },
    clear: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      setToken(null);
      setUsername(null);
    },
  };
};

export const useAuth = () => useContext(AuthContext);
