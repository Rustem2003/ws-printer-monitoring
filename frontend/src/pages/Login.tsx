import { FormEvent, useState } from 'react';
import { Box, Button, Paper, TextField, Typography, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { useT } from '../i18n';
import Footer from '../components/Footer';

export default function Login() {
  const auth = useAuth();
  const nav = useNavigate();
  const { t } = useT();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post('/auth/login', { username, password });
      auth.setSession(res.data.access_token, username);
      nav('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('login.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
        <Paper sx={{ p: 4, width: 380 }} component="form" onSubmit={submit}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
            <Box component="img" src="/logo.svg" alt="WS" sx={{ width: 100, height: 100, mb: 1.5 }} />
            <Typography variant="h5" sx={{ fontWeight: 700 }}>{t('login.title')}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{t('login.subtitle')}</Typography>
          </Box>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <TextField fullWidth label={t('login.username')} value={username} onChange={(e) => setUsername(e.target.value)} margin="normal" />
          <TextField fullWidth label={t('login.password')} type="password" value={password} onChange={(e) => setPassword(e.target.value)} margin="normal" />
          <Button type="submit" fullWidth variant="contained" sx={{ mt: 2 }} disabled={busy}>
            {busy ? t('login.submitting') : t('login.submit')}
          </Button>
        </Paper>
      </Box>
      <Footer />
    </Box>
  );
}
