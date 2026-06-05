import { useMemo, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Printers from './pages/Printers';
import Events from './pages/Events';
import Telegram from './pages/Telegram';
import NotificationSettings from './pages/NotificationSettings';
import BotSettings from './pages/BotSettings';
import Shell from './components/Shell';
import { AuthContext, useAuthState } from './auth';

export default function App() {
  const auth = useAuthState();
  const [mode, setMode] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('theme') as 'dark' | 'light') || 'dark',
  );
  const theme = useMemo(() => createTheme({ palette: { mode } }), [mode]);
  const toggleTheme = () => {
    const next = mode === 'dark' ? 'light' : 'dark';
    setMode(next);
    localStorage.setItem('theme', next);
  };

  const Protected = ({ children }: { children: JSX.Element }) =>
    auth.token ? <Shell toggleTheme={toggleTheme} mode={mode}>{children}</Shell> : <Navigate to="/login" replace />;

  return (
    <AuthContext.Provider value={auth}>
      <ThemeProvider theme={theme}>
        <Routes>
          <Route path="/login" element={auth.token ? <Navigate to="/" /> : <Login />} />
          <Route path="/" element={<Protected><Dashboard /></Protected>} />
          <Route path="/printers" element={<Protected><Printers /></Protected>} />
          <Route path="/events" element={<Protected><Events /></Protected>} />
          <Route path="/telegram" element={<Protected><Telegram /></Protected>} />
          <Route path="/notification-settings" element={<Protected><NotificationSettings /></Protected>} />
          <Route path="/bot-settings" element={<Protected><BotSettings /></Protected>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}
