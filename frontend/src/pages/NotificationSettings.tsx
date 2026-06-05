import { useEffect, useState } from 'react';
import {
  Alert, Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  CircularProgress, Button, TextField, Switch, Stack, MenuItem,
} from '@mui/material';
import RestoreIcon from '@mui/icons-material/Restore';
import SaveIcon from '@mui/icons-material/Save';
import { api } from '../api';
import { useT } from '../i18n';

type Setting = {
  event_type: string;
  title_ru?: string;
  enabled: boolean;
  repeat_interval_minutes: number;
};

export default function NotificationSettings() {
  const { t } = useT();
  const [rows, setRows] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null);

  const PRESETS = [
    { value: 0, label: t('ns.preset.once') },
    { value: 5, label: t('ns.preset.5m') },
    { value: 15, label: t('ns.preset.15m') },
    { value: 30, label: t('ns.preset.30m') },
    { value: 60, label: t('ns.preset.1h') },
    { value: 120, label: t('ns.preset.2h') },
    { value: 240, label: t('ns.preset.4h') },
    { value: 480, label: t('ns.preset.8h') },
    { value: 720, label: t('ns.preset.12h') },
    { value: 1440, label: t('ns.preset.1d') },
  ];

  const fmtPeriod = (min: number): string => {
    if (min === 0) return t('ns.preset.once');
    if (min < 60) return `${min} min`;
    if (min < 1440) return `${(min / 60).toFixed(min % 60 === 0 ? 0 : 1)} h`;
    return `${(min / 1440).toFixed(min % 1440 === 0 ? 0 : 1)} d`;
  };

  const reload = () => {
    setLoading(true);
    api.get('/notification-settings')
      .then((r) => setRows(r.data || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(reload, []);

  const update = async (et: string, patch: Partial<Setting>) => {
    setSavingKey(et);
    try {
      const r = await api.put(`/notification-settings/${et}`, patch);
      setRows((s) => s.map((x) => x.event_type === et ? r.data : x));
      setFlash({ kind: 'success', text: `«${r.data.title_ru || et}» ${t('ns.updated')}` });
    } catch (e: any) {
      setFlash({ kind: 'error', text: e?.response?.data?.detail || t('ns.save_err') });
    } finally {
      setSavingKey(null);
    }
  };

  const resetAll = async () => {
    if (!window.confirm(t('ns.reset_confirm'))) return;
    setLoading(true);
    try {
      const r = await api.post('/notification-settings/reset');
      setRows(r.data || []);
      setFlash({ kind: 'success', text: t('ns.reset_ok') });
    } catch (e: any) {
      setFlash({ kind: 'error', text: e?.response?.data?.detail || t('ns.reset_err') });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{t('ns.title')}</Typography>
        <Button startIcon={<RestoreIcon />} onClick={resetAll} variant="outlined" color="warning">
          {t('ns.reset')}
        </Button>
      </Box>

      {flash && <Alert severity={flash.kind} sx={{ mb: 2 }} onClose={() => setFlash(null)}>{flash.text}</Alert>}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">{t('ns.hint')}</Typography>
      </Paper>

      <Paper>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('ns.col_event')}</TableCell>
                <TableCell>event_type</TableCell>
                <TableCell align="center">{t('ns.col_enabled')}</TableCell>
                <TableCell>{t('ns.col_period')}</TableCell>
                <TableCell>{t('ns.col_custom')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={5} align="center">{t('ns.empty')}</TableCell></TableRow>
              ) : rows.map((r) => (
                <TableRow key={r.event_type} hover>
                  <TableCell><strong>{r.title_ru || r.event_type}</strong></TableCell>
                  <TableCell><code>{r.event_type}</code></TableCell>
                  <TableCell align="center">
                    <Switch
                      checked={r.enabled}
                      onChange={(e) => update(r.event_type, { enabled: e.target.checked })}
                      disabled={savingKey === r.event_type}
                    />
                  </TableCell>
                  <TableCell sx={{ minWidth: 240 }}>
                    <TextField
                      select size="small" fullWidth
                      value={PRESETS.find((p) => p.value === r.repeat_interval_minutes) ? r.repeat_interval_minutes : -1}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        if (val >= 0) update(r.event_type, { repeat_interval_minutes: val });
                      }}
                      disabled={!r.enabled || savingKey === r.event_type}
                    >
                      {PRESETS.map((p) => (
                        <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                      ))}
                      {!PRESETS.find((p) => p.value === r.repeat_interval_minutes) && (
                        <MenuItem value={-1} disabled>
                          {t('ns.custom_label')}: {fmtPeriod(r.repeat_interval_minutes)}
                        </MenuItem>
                      )}
                    </TextField>
                  </TableCell>
                  <TableCell sx={{ minWidth: 160 }}>
                    <CustomMinutes
                      value={r.repeat_interval_minutes}
                      disabled={!r.enabled || savingKey === r.event_type}
                      onSave={(v) => update(r.event_type, { repeat_interval_minutes: v })}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
}

function CustomMinutes({ value, disabled, onSave }: { value: number; disabled?: boolean; onSave: (v: number) => void }) {
  const { t } = useT();
  const [v, setV] = useState<string>(String(value));
  useEffect(() => { setV(String(value)); }, [value]);
  const dirty = String(value) !== v;
  return (
    <Stack direction="row" spacing={1}>
      <TextField
        size="small" type="number"
        inputProps={{ min: 0, max: 10080 }}
        value={v}
        onChange={(e) => setV(e.target.value)}
        disabled={disabled}
        sx={{ width: 90 }}
      />
      <Button
        size="small" variant="contained"
        startIcon={<SaveIcon />}
        disabled={disabled || !dirty || v === ''}
        onClick={() => {
          const n = Number(v);
          if (Number.isFinite(n) && n >= 0 && n <= 10080) onSave(n);
        }}
      >
        {t('btn.ok')}
      </Button>
    </Stack>
  );
}
