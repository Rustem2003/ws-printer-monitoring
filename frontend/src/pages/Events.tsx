import { useEffect, useState } from 'react';
import {
  Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Chip,
  CircularProgress, Stack, TextField, MenuItem, Button,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { api } from '../api';
import { useT } from '../i18n';

type Event = {
  id: number;
  printer_id?: number;
  event_type: string;
  severity?: string;
  message?: string;
  created_at?: string;
  printer_name?: string;
  printer_ip?: string;
  printer_location?: string;
};

const EVENT_TYPES = [
  'offline', 'no_response', 'paper_jam', 'no_paper', 'open_cover',
  'toner_error', 'fuser_error', 'drum_error', 'service_required', 'discovered',
];

const sevColor = (s?: string): any =>
  s === 'critical' ? 'error' : s === 'warning' ? 'warning' : 'default';

export default function Events() {
  const { t } = useT();
  const [rows, setRows] = useState<Event[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState('');
  const [eventType, setEventType] = useState('');

  const reload = () => {
    setLoading(true);
    const params: any = { page_size: 100 };
    if (severity) params.severity = severity;
    if (eventType) params.event_type = eventType;
    api.get('/events', { params })
      .then((r) => { setRows(r.data?.items || []); setTotal(r.data?.total ?? 0); })
      .catch(() => { setRows([]); setTotal(0); })
      .finally(() => setLoading(false));
  };

  useEffect(reload, [severity, eventType]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{t('events.title')} ({total})</Typography>
        <Button startIcon={<RefreshIcon />} onClick={reload} variant="outlined">{t('btn.refresh')}</Button>
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2}>
          <TextField
            select label={t('events.filter.severity')} size="small" sx={{ minWidth: 160 }}
            value={severity} onChange={(e) => setSeverity(e.target.value)}
          >
            <MenuItem value="">{t('events.filter.all')}</MenuItem>
            <MenuItem value="critical">Critical</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="info">Info</MenuItem>
          </TextField>
          <TextField
            select label={t('events.filter.type')} size="small" sx={{ minWidth: 220 }}
            value={eventType} onChange={(e) => setEventType(e.target.value)}
          >
            <MenuItem value="">{t('events.filter.all')}</MenuItem>
            {EVENT_TYPES.map((et) => <MenuItem key={et} value={et}>{et}</MenuItem>)}
          </TextField>
        </Stack>
      </Paper>

      <Paper>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('col.time')}</TableCell>
                <TableCell>{t('col.printer')}</TableCell>
                <TableCell>{t('col.ip')}</TableCell>
                <TableCell>{t('col.location')}</TableCell>
                <TableCell>{t('col.type')}</TableCell>
                <TableCell>{t('col.severity')}</TableCell>
                <TableCell>{t('col.message')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={7} align="center">{t('events.empty')}</TableCell></TableRow>
              ) : rows.map((e) => (
                <TableRow key={e.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {e.created_at?.replace('T', ' ').slice(0, 19) || '—'}
                  </TableCell>
                  <TableCell>{e.printer_name || `#${e.printer_id}`}</TableCell>
                  <TableCell>{e.printer_ip || '—'}</TableCell>
                  <TableCell><strong>{e.printer_location || '—'}</strong></TableCell>
                  <TableCell><Chip label={e.event_type} size="small" /></TableCell>
                  <TableCell>
                    <Chip size="small" label={(e.severity || 'info').toUpperCase()} color={sevColor(e.severity)} />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 480 }}>{e.message || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
}
