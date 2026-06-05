import { useEffect, useState } from 'react';
import {
  Alert, Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  Chip, CircularProgress, Button, TextField, Stack, Dialog, DialogTitle, DialogContent,
  DialogActions, IconButton, MenuItem, FormGroup, FormControlLabel, Checkbox, Switch,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SendIcon from '@mui/icons-material/Send';
import { api } from '../api';
import { useT } from '../i18n';

type Chat = {
  id: number;
  chat_id: string;
  name?: string;
  chat_type: string;
  is_active: number;
  subscribed_events?: string;
};

const ALL_EVENTS = [
  'offline', 'paper_jam', 'no_paper', 'open_cover', 'scanner_error',
  'fuser_error', 'drum_error', 'toner_error', 'service_required',
  'maintenance_required', 'discovered',
];

type FormState = {
  chat_id: string;
  name: string;
  chat_type: string;
  is_active: boolean;
  events: Set<string>;
};

const emptyForm = (): FormState => ({
  chat_id: '', name: '', chat_type: 'group', is_active: true,
  events: new Set(['offline', 'paper_jam', 'no_paper', 'toner_error', 'service_required']),
});

export default function Telegram() {
  const { t } = useT();
  const [rows, setRows] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null);

  const [dlgOpen, setDlgOpen] = useState(false);
  const [dlgMode, setDlgMode] = useState<'add' | 'edit'>('add');
  const [dlgTarget, setDlgTarget] = useState<Chat | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [busy, setBusy] = useState(false);
  const [dlgErr, setDlgErr] = useState<string | null>(null);

  const [delTarget, setDelTarget] = useState<Chat | null>(null);

  const CHAT_TYPES = [
    { value: 'private', label: t('tg.type.private') },
    { value: 'group', label: t('tg.type.group') },
    { value: 'channel', label: t('tg.type.channel') },
  ];

  const reload = () => {
    setLoading(true);
    api.get('/telegram-chats')
      .then((r) => setRows(r.data || []))
      .catch((e) => setError(e?.response?.data?.detail || t('tg.load_err')))
      .finally(() => setLoading(false));
  };

  useEffect(reload, []);

  const openAdd = () => {
    setDlgMode('add'); setDlgTarget(null); setForm(emptyForm()); setDlgErr(null); setDlgOpen(true);
  };

  const openEdit = (c: Chat) => {
    setDlgMode('edit'); setDlgTarget(c);
    setForm({
      chat_id: c.chat_id, name: c.name || '', chat_type: c.chat_type,
      is_active: !!c.is_active,
      events: new Set((c.subscribed_events || '').split(',').map((s) => s.trim()).filter(Boolean)),
    });
    setDlgErr(null); setDlgOpen(true);
  };

  const toggleEvent = (e: string) => {
    const next = new Set(form.events);
    if (next.has(e)) next.delete(e); else next.add(e);
    setForm({ ...form, events: next });
  };

  const submit = async () => {
    setDlgErr(null);
    if (!form.chat_id.trim()) { setDlgErr(t('tg.required_err')); return; }
    setBusy(true);
    const payload = {
      chat_id: form.chat_id.trim(),
      name: form.name.trim() || null,
      chat_type: form.chat_type,
      is_active: form.is_active ? 1 : 0,
      subscribed_events: Array.from(form.events).join(',') || null,
    };
    try {
      if (dlgMode === 'add') {
        await api.post('/telegram-chats', payload);
      } else if (dlgTarget) {
        const { chat_id, ...upd } = payload;
        await api.put(`/telegram-chats/${dlgTarget.id}`, upd);
      }
      setDlgOpen(false); reload();
    } catch (e: any) {
      setDlgErr(e?.response?.data?.detail || t('tg.save_err'));
    } finally {
      setBusy(false);
    }
  };

  const sendTest = async (c: Chat) => {
    setFlash({ kind: 'info', text: `${t('tg.sending')} «${c.name || c.chat_id}»…` });
    try {
      const r = await api.post(`/telegram-chats/${c.id}/test`);
      if (r.data?.ok) {
        setFlash({ kind: 'success', text: `${t('tg.sent_ok')} «${c.name || c.chat_id}» ✅` });
      } else {
        setFlash({ kind: 'error', text: `${t('tg.sent_err')}: ${JSON.stringify(r.data?.response).slice(0, 200)}` });
      }
    } catch (e: any) {
      setFlash({ kind: 'error', text: e?.response?.data?.detail || t('tg.send_err') });
    }
  };

  const confirmDelete = async () => {
    if (!delTarget) return;
    try { await api.delete(`/telegram-chats/${delTarget.id}`); setDelTarget(null); reload(); } catch { setDelTarget(null); }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{t('tg.title')}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openAdd}>{t('tg.add')}</Button>
      </Box>

      {flash && <Alert severity={flash.kind} sx={{ mb: 2 }} onClose={() => setFlash(null)}>{flash.text}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">{t('tg.hint')}</Typography>
      </Paper>

      <Paper>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('col.id')}</TableCell>
                <TableCell>{t('tg.chat_id')}</TableCell>
                <TableCell>{t('col.name')}</TableCell>
                <TableCell>{t('tg.col_type')}</TableCell>
                <TableCell>{t('tg.col_active')}</TableCell>
                <TableCell>{t('tg.col_subs')}</TableCell>
                <TableCell align="right">{t('col.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={7} align="center">{t('tg.empty')}</TableCell></TableRow>
              ) : rows.map((c) => {
                const evs = (c.subscribed_events || '').split(',').map((s) => s.trim()).filter(Boolean);
                return (
                  <TableRow key={c.id} hover>
                    <TableCell>{c.id}</TableCell>
                    <TableCell><code>{c.chat_id}</code></TableCell>
                    <TableCell>{c.name || '—'}</TableCell>
                    <TableCell>{c.chat_type}</TableCell>
                    <TableCell>
                      <Chip label={c.is_active ? 'on' : 'off'} color={c.is_active ? 'success' : 'default'} size="small" />
                    </TableCell>
                    <TableCell sx={{ maxWidth: 360 }}>
                      {evs.length === 0 ? <em>—</em> : (
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {evs.map((e) => <Chip key={e} label={e} size="small" />)}
                        </Stack>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => sendTest(c)} title={t('tg.test')} color="primary"><SendIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => openEdit(c)} title={t('printers.edit')}><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => setDelTarget(c)} title={t('printers.delete')} color="error"><DeleteIcon fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Paper>

      <Dialog open={dlgOpen} onClose={() => setDlgOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{dlgMode === 'add' ? t('tg.add_dlg') : `${t('tg.edit_dlg')} #${dlgTarget?.id ?? ''}`}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {dlgErr && <Alert severity="error">{dlgErr}</Alert>}
            <TextField
              label={t('tg.f_chatid')} value={form.chat_id}
              onChange={(e) => setForm({ ...form, chat_id: e.target.value })}
              required autoFocus disabled={dlgMode === 'edit'}
              placeholder="237310013"
              helperText={dlgMode === 'edit' ? t('tg.f_chatid_locked') : t('tg.f_chatid_hint')}
            />
            <TextField label={t('tg.f_name')} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <TextField label={t('tg.f_type')} value={form.chat_type} onChange={(e) => setForm({ ...form, chat_type: e.target.value })} select>
              {CHAT_TYPES.map((t_) => <MenuItem key={t_.value} value={t_.value}>{t_.label}</MenuItem>)}
            </TextField>
            <FormControlLabel
              control={<Switch checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />}
              label={t('tg.active_label')}
            />
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>{t('tg.subs_label')}</Typography>
              <FormGroup row>
                {ALL_EVENTS.map((e) => (
                  <FormControlLabel
                    key={e}
                    control={<Checkbox checked={form.events.has(e)} onChange={() => toggleEvent(e)} size="small" />}
                    label={e}
                    sx={{ minWidth: '45%' }}
                  />
                ))}
              </FormGroup>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDlgOpen(false)}>{t('btn.cancel')}</Button>
          <Button variant="contained" onClick={submit} disabled={busy}>
            {busy ? t('btn.saving') : (dlgMode === 'add' ? t('btn.add') : t('btn.save'))}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!delTarget} onClose={() => setDelTarget(null)}>
        <DialogTitle>{t('tg.delete_q')}</DialogTitle>
        <DialogContent>
          <Typography>{delTarget?.name || delTarget?.chat_id} — {t('tg.delete_warning')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDelTarget(null)}>{t('btn.cancel')}</Button>
          <Button color="error" variant="contained" onClick={confirmDelete}>{t('btn.delete')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
