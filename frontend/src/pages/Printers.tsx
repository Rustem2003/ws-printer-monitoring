import { useEffect, useState } from 'react';
import {
  Alert, Box, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  Chip, CircularProgress, Button, TextField, Stack, Dialog, DialogTitle, DialogContent,
  DialogActions, IconButton, MenuItem, LinearProgress,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import { api } from '../api';
import { useT } from '../i18n';

type Printer = {
  id: number;
  name?: string;
  ip_address: string;
  vendor?: string;
  model?: string;
  is_online: boolean;
  serial_number?: string;
  location?: string;
  last_seen?: string;
};

type Consumable = {
  id: number;
  name: string;
  current_level?: number | null;
  max_capacity?: number | null;
};

const VENDORS = ['HP', 'Xerox', 'Canon', 'Brother', 'Kyocera', 'Ricoh', 'Konica Minolta', 'Epson', 'Unknown'];
const SUBNET_RE = /^(?:\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;

const colorOf = (name: string): string => {
  const n = name.toLowerCase();
  if (n.includes('black') || n.includes('bk')) return '#222';
  if (n.includes('cyan')) return '#00B0E0';
  if (n.includes('magenta')) return '#D9006C';
  if (n.includes('yellow')) return '#F7D000';
  if (n.includes('drum')) return '#7B5BAA';
  if (n.includes('fuser')) return '#C2410C';
  return '#555';
};

const levelPct = (c: Consumable): number | null => {
  if (c.current_level == null) return null;
  if (c.max_capacity && c.max_capacity > 0) return Math.max(0, Math.min(100, (c.current_level / c.max_capacity) * 100));
  if (c.current_level >= 0 && c.current_level <= 100) return c.current_level;
  return null;
};

const emptyForm = {
  name: '', ip_address: '', location: '', vendor: '', model: '',
  snmp_community: 'public', snmp_version: '2c',
};

export default function Printers() {
  const { t } = useT();
  const [rows, setRows] = useState<Printer[]>([]);
  const [loading, setLoading] = useState(true);

  const [subnet, setSubnet] = useState(() => localStorage.getItem('lastSubnet') || '192.168.0.0/24');
  const [subnetError, setSubnetError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<{ kind: 'info' | 'success' | 'error'; text: string } | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState(emptyForm);
  const [addErr, setAddErr] = useState<string | null>(null);
  const [addBusy, setAddBusy] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Printer | null>(null);
  const [editForm, setEditForm] = useState({
    name: '', location: '', vendor: '', model: '',
    snmp_version: '2c', snmp_community: 'public',
  });
  const [editErr, setEditErr] = useState<string | null>(null);

  const [delTarget, setDelTarget] = useState<Printer | null>(null);

  const [consumables, setConsumables] = useState<Record<number, Consumable[]>>({});
  const [checking, setChecking] = useState<Record<number, boolean>>({});

  const loadConsumables = async (printers: Printer[]) => {
    const out: Record<number, Consumable[]> = {};
    await Promise.all(printers.map(async (p) => {
      try {
        const r = await api.get(`/printers/${p.id}/consumables`);
        out[p.id] = r.data || [];
      } catch { out[p.id] = []; }
    }));
    setConsumables(out);
  };

  const reload = () => {
    setLoading(true);
    api.get('/printers')
      .then((r) => {
        const list: Printer[] = r.data?.items || r.data || [];
        setRows(list);
        loadConsumables(list);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(reload, []);

  const checkNow = async (p: Printer) => {
    setChecking((s) => ({ ...s, [p.id]: true }));
    try {
      await api.post(`/printers/${p.id}/check`);
      setTimeout(reload, 800);
    } catch (e: any) {
      setScanMsg({ kind: 'error', text: `${t('printers.scan_error')}: ${e?.response?.data?.detail || ''}` });
    } finally {
      setChecking((s) => ({ ...s, [p.id]: false }));
    }
  };

  const validateSubnet = (s: string): string | null => {
    if (!SUBNET_RE.test(s)) return t('printers.subnet_error');
    const [ip, mask] = s.split('/');
    if (Number(mask) < 8 || Number(mask) > 32) return t('printers.subnet_error');
    if (ip.split('.').some((p) => Number(p) > 255)) return t('printers.subnet_error');
    return null;
  };

  const scan = async () => {
    const err = validateSubnet(subnet);
    if (err) { setSubnetError(err); return; }
    setSubnetError(null);
    localStorage.setItem('lastSubnet', subnet);
    setScanning(true);
    setScanMsg({ kind: 'info', text: `${t('printers.scan_started')} ${subnet} …` });
    try {
      await api.post('/discovery/start', { subnet, method: 'snmp_broadcast' });
      setTimeout(() => {
        reload();
        setScanMsg({ kind: 'success', text: t('printers.scan_done') });
        setScanning(false);
      }, 25000);
    } catch (e: any) {
      setScanMsg({ kind: 'error', text: `${t('printers.scan_error')}: ${e?.response?.data?.detail || ''}` });
      setScanning(false);
    }
  };

  const submitAdd = async () => {
    setAddErr(null);
    if (!addForm.name.trim() || !addForm.ip_address.trim()) {
      setAddErr(t('printers.required_err'));
      return;
    }
    setAddBusy(true);
    try {
      const payload: any = { ...addForm };
      if (!payload.vendor) delete payload.vendor;
      if (!payload.model) delete payload.model;
      if (!payload.location) delete payload.location;
      await api.post('/printers', payload);
      setAddOpen(false);
      setAddForm(emptyForm);
      reload();
    } catch (e: any) {
      setAddErr(e?.response?.data?.detail || t('printers.add_err'));
    } finally {
      setAddBusy(false);
    }
  };

  const openEdit = async (p: Printer) => {
    setEditTarget(p);
    setEditForm({
      name: p.name || '', location: p.location || '',
      vendor: p.vendor || '', model: p.model || '',
      snmp_version: '2c', snmp_community: 'public',
    });
    setEditErr(null);
    setEditOpen(true);
    try {
      const r = await api.get(`/printers/${p.id}`);
      setEditForm((s) => ({
        ...s,
        snmp_version: r.data.snmp_version || '2c',
        snmp_community: r.data.snmp_community || 'public',
      }));
    } catch {}
  };

  const submitEdit = async () => {
    if (!editTarget) return;
    setEditErr(null);
    try {
      await api.put(`/printers/${editTarget.id}`, {
        name: editForm.name,
        location: editForm.location,
        vendor: editForm.vendor || null,
        model: editForm.model || null,
        snmp_version: editForm.snmp_version,
        snmp_community: editForm.snmp_community,
      });
      setEditOpen(false);
      reload();
    } catch (e: any) {
      setEditErr(e?.response?.data?.detail || t('printers.save_err'));
    }
  };

  const confirmDelete = async () => {
    if (!delTarget) return;
    try {
      await api.delete(`/printers/${delTarget.id}`);
      setDelTarget(null);
      reload();
    } catch { setDelTarget(null); }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{t('printers.title')}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
          {t('printers.add_manual')}
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>{t('printers.scan_title')}</Typography>
        <Stack direction="row" spacing={2} alignItems="flex-start">
          <TextField
            label={t('printers.subnet')}
            value={subnet}
            onChange={(e) => { setSubnet(e.target.value); setSubnetError(null); }}
            placeholder="192.168.0.0/24"
            size="small"
            error={!!subnetError}
            helperText={subnetError || t('printers.subnet_help')}
            disabled={scanning}
            sx={{ minWidth: 320 }}
          />
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={scan}
            disabled={scanning}
            sx={{ mt: 0.5 }}
          >
            {scanning ? t('printers.scanning') : t('printers.scan')}
          </Button>
        </Stack>
        {scanMsg && <Alert severity={scanMsg.kind} sx={{ mt: 2 }}>{scanMsg.text}</Alert>}
      </Paper>

      <Paper>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('col.id')}</TableCell>
                <TableCell>{t('col.name')}</TableCell>
                <TableCell>{t('col.ip')}</TableCell>
                <TableCell>{t('col.location')}</TableCell>
                <TableCell>{t('col.vendor')}</TableCell>
                <TableCell>{t('col.consumables')}</TableCell>
                <TableCell>{t('col.serial')}</TableCell>
                <TableCell>{t('col.status')}</TableCell>
                <TableCell align="right">{t('col.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={9} align="center">{t('printers.empty')}</TableCell></TableRow>
              ) : rows.map((p) => (
                <TableRow key={p.id} hover sx={{ verticalAlign: 'top' }}>
                  <TableCell>{p.id}</TableCell>
                  <TableCell>{p.name || '—'}</TableCell>
                  <TableCell>{p.ip_address}</TableCell>
                  <TableCell>{p.location || '—'}</TableCell>
                  <TableCell>{p.vendor || '—'}</TableCell>
                  <TableCell sx={{ minWidth: 220 }}>
                    {(consumables[p.id] && consumables[p.id].length > 0) ? (
                      <Stack spacing={0.5}>
                        {consumables[p.id].map((c) => {
                          const pct = levelPct(c);
                          return (
                            <Box key={c.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="caption" sx={{ minWidth: 64 }}>{c.name}</Typography>
                              {pct == null ? (
                                <Typography variant="caption" color="text.secondary">—</Typography>
                              ) : (
                                <>
                                  <LinearProgress
                                    variant="determinate"
                                    value={pct}
                                    sx={{
                                      flexGrow: 1, height: 8, borderRadius: 4,
                                      backgroundColor: '#3334',
                                      '& .MuiLinearProgress-bar': { backgroundColor: colorOf(c.name) },
                                    }}
                                  />
                                  <Typography variant="caption" sx={{ minWidth: 36, textAlign: 'right' }}>
                                    {pct.toFixed(0)}%
                                  </Typography>
                                </>
                              )}
                            </Box>
                          );
                        })}
                      </Stack>
                    ) : <Typography variant="caption" color="text.secondary">{t('status.no_data')}</Typography>}
                  </TableCell>
                  <TableCell>{p.serial_number || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      label={p.is_online ? t('status.online') : t('status.offline')}
                      color={p.is_online ? 'success' : 'default'} size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => checkNow(p)} title={t('printers.check_now')} color="primary" disabled={!!checking[p.id]}>
                      <RefreshIcon fontSize="small" sx={checking[p.id] ? { animation: 'spin 1s linear infinite', '@keyframes spin': { from: { transform: 'rotate(0)' }, to: { transform: 'rotate(360deg)' } } } : {}} />
                    </IconButton>
                    <IconButton size="small" onClick={() => openEdit(p)} title={t('printers.edit')}><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" onClick={() => setDelTarget(p)} title={t('printers.delete')} color="error"><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t('printers.add_dlg_title')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {addErr && <Alert severity="error">{addErr}</Alert>}
            <TextField label={t('printers.f_name')} value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} required autoFocus />
            <TextField label={t('printers.f_ip')} value={addForm.ip_address} onChange={(e) => setAddForm({ ...addForm, ip_address: e.target.value })} placeholder="192.168.0.100" required />
            <TextField label={t('printers.f_location')} value={addForm.location} onChange={(e) => setAddForm({ ...addForm, location: e.target.value })} placeholder={t('printers.f_location_hint')} />
            <TextField label={t('printers.f_vendor')} value={addForm.vendor} onChange={(e) => setAddForm({ ...addForm, vendor: e.target.value })} select>
              <MenuItem value="">—</MenuItem>
              {VENDORS.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
            </TextField>
            <TextField label={t('printers.f_model')} value={addForm.model} onChange={(e) => setAddForm({ ...addForm, model: e.target.value })} />
            <Stack direction="row" spacing={2}>
              <TextField label={t('printers.f_community')} value={addForm.snmp_community} onChange={(e) => setAddForm({ ...addForm, snmp_community: e.target.value })} fullWidth />
              <TextField label={t('printers.f_version')} value={addForm.snmp_version} onChange={(e) => setAddForm({ ...addForm, snmp_version: e.target.value })} select sx={{ minWidth: 120 }}>
                <MenuItem value="1">1</MenuItem>
                <MenuItem value="2c">2c</MenuItem>
                <MenuItem value="3">3</MenuItem>
              </TextField>
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>{t('btn.cancel')}</Button>
          <Button variant="contained" onClick={submitAdd} disabled={addBusy}>
            {addBusy ? t('btn.saving') : t('btn.add')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t('printers.edit_dlg_title')}{editTarget ? ` #${editTarget.id}` : ''}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {editErr && <Alert severity="error">{editErr}</Alert>}
            {editTarget && <Typography variant="body2" color="text.secondary">IP: {editTarget.ip_address}</Typography>}
            <TextField label={t('printers.f_name')} value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} autoFocus />
            <TextField label={t('printers.f_location')} value={editForm.location} onChange={(e) => setEditForm({ ...editForm, location: e.target.value })} placeholder={t('printers.f_location_hint')} />
            <TextField label={t('printers.f_vendor')} value={editForm.vendor} onChange={(e) => setEditForm({ ...editForm, vendor: e.target.value })} select>
              <MenuItem value="">—</MenuItem>
              {VENDORS.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
            </TextField>
            <TextField label={t('printers.f_model')} value={editForm.model} onChange={(e) => setEditForm({ ...editForm, model: e.target.value })} />
            <Stack direction="row" spacing={2}>
              <TextField label={t('printers.f_community')} value={editForm.snmp_community} onChange={(e) => setEditForm({ ...editForm, snmp_community: e.target.value })} fullWidth helperText={t('printers.f_community_hint')} />
              <TextField label={t('printers.f_version')} value={editForm.snmp_version} onChange={(e) => setEditForm({ ...editForm, snmp_version: e.target.value })} select sx={{ minWidth: 140 }} helperText={t('printers.f_version_hint')}>
                <MenuItem value="1">1</MenuItem>
                <MenuItem value="2c">2c</MenuItem>
                <MenuItem value="3">3</MenuItem>
              </TextField>
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{t('btn.cancel')}</Button>
          <Button variant="contained" onClick={submitEdit}>{t('btn.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!delTarget} onClose={() => setDelTarget(null)}>
        <DialogTitle>{t('printers.delete_q')}</DialogTitle>
        <DialogContent>
          <Typography>{delTarget?.name || delTarget?.ip_address} {t('printers.delete_warning')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDelTarget(null)}>{t('btn.cancel')}</Button>
          <Button color="error" variant="contained" onClick={confirmDelete}>{t('btn.delete')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
