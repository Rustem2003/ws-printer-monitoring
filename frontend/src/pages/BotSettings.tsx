import { useEffect, useState } from 'react';
import {
  Alert, Box, Typography, Paper, TextField, Stack, Button, Chip, InputAdornment,
  IconButton, CircularProgress, Divider,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import SaveIcon from '@mui/icons-material/Save';
import ScienceIcon from '@mui/icons-material/Science';
import { api } from '../api';
import { useT } from '../i18n';

type BotInfo = {
  token_masked?: string;
  token_set: boolean;
  chat_id?: string;
  admin_chat_id?: string;
  source: 'db' | 'env' | 'none';
};

type TestResult = {
  ok: boolean;
  bot_id?: number;
  username?: string;
  first_name?: string;
  error_code?: number;
  description?: string;
};

export default function BotSettings() {
  const { t } = useT();
  const [info, setInfo] = useState<BotInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const [token, setToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [adminChatId, setAdminChatId] = useState('');
  const [showToken, setShowToken] = useState(false);

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [flash, setFlash] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);

  const reload = () => {
    setLoading(true);
    api.get('/system-settings/telegram')
      .then((r) => {
        setInfo(r.data);
        setChatId(r.data.chat_id || '');
        setAdminChatId(r.data.admin_chat_id || '');
        setToken('');
      })
      .catch(() => setInfo(null))
      .finally(() => setLoading(false));
  };

  useEffect(reload, []);

  const save = async () => {
    setSaving(true);
    setFlash(null);
    try {
      const payload: any = { chat_id: chatId, admin_chat_id: adminChatId };
      if (token.trim()) payload.token = token.trim();
      const r = await api.put('/system-settings/telegram', payload);
      setInfo(r.data);
      setToken('');
      setFlash({ kind: 'success', text: t('bot.saved') });
    } catch (e: any) {
      setFlash({ kind: 'error', text: e?.response?.data?.detail || t('bot.save_err') });
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post('/system-settings/telegram/test');
      setTestResult(r.data);
    } catch (e: any) {
      setTestResult({ ok: false, description: e?.response?.data?.detail || 'error' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;

  const sourceLabel = info ? t(`bot.token_source.${info.source}`) : '';

  return (
    <Box>
      <Typography variant="h4" gutterBottom>{t('bot.title')}</Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">{t('bot.hint')}</Typography>
      </Paper>

      {flash && <Alert severity={flash.kind} sx={{ mb: 2 }} onClose={() => setFlash(null)}>{flash.text}</Alert>}

      <Paper sx={{ p: 3, mb: 2 }}>
        <Stack spacing={2}>
          {info && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Typography variant="body2"><strong>{t('bot.token_current')}:</strong></Typography>
              {info.token_set ? (
                <>
                  <Box component="code" sx={{ fontFamily: 'monospace', bgcolor: 'action.hover', px: 1, py: 0.5, borderRadius: 1 }}>
                    {info.token_masked}
                  </Box>
                  <Chip label={sourceLabel} size="small" color={info.source === 'db' ? 'success' : 'default'} />
                </>
              ) : (
                <Chip label={t('bot.token_source.none')} size="small" color="warning" />
              )}
              <Button
                size="small"
                variant="outlined"
                startIcon={testing ? <CircularProgress size={14} /> : <ScienceIcon />}
                onClick={test}
                disabled={testing || !info.token_set}
              >
                {testing ? t('bot.testing') : t('bot.btn_test')}
              </Button>
            </Box>
          )}

          {testResult && (
            <Alert severity={testResult.ok ? 'success' : 'error'} onClose={() => setTestResult(null)}>
              {testResult.ok ? (
                <>
                  ✅ {t('bot.test_ok')}: <strong>@{testResult.username}</strong>
                  {' '}({testResult.first_name}, id={testResult.bot_id})
                </>
              ) : (
                <>
                  ❌ {t('bot.test_err')}: <code>{testResult.description}</code>
                </>
              )}
            </Alert>
          )}

          <Divider />

          <TextField
            label={t('bot.token_label')}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="123456789:AAEABCDEFGhijklmn-OPQrstuv_wxyz"
            type={showToken ? 'text' : 'password'}
            helperText={t('bot.token_hint')}
            fullWidth
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowToken((s) => !s)} edge="end" title={showToken ? t('bot.hide_token') : t('bot.show_token')}>
                    {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <TextField
              label={t('bot.chat_label')}
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              helperText={t('bot.chat_hint')}
              fullWidth
              placeholder="237310013"
            />
            <TextField
              label={t('bot.admin_label')}
              value={adminChatId}
              onChange={(e) => setAdminChatId(e.target.value)}
              helperText={t('bot.admin_hint')}
              fullWidth
              placeholder="237310013"
            />
          </Stack>

          <Box>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={save}
              disabled={saving}
              size="large"
            >
              {saving ? t('btn.saving') : t('bot.btn_save')}
            </Button>
          </Box>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>{t('bot.your_id_question')}</Typography>
        <Typography variant="body2" color="text.secondary">{t('bot.your_id_answer')}</Typography>
      </Paper>
    </Box>
  );
}
