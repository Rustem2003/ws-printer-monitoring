import { useEffect, useState } from 'react';
import {
  Grid, Paper, Typography, Box, CircularProgress, Stack, Chip, LinearProgress, Avatar,
  Table, TableHead, TableRow, TableCell, TableBody,
} from '@mui/material';
import PrintIcon from '@mui/icons-material/Print';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import ErrorIcon from '@mui/icons-material/Error';
import InvertColorsIcon from '@mui/icons-material/InvertColors';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
} from 'recharts';
import { api } from '../api';
import { useT } from '../i18n';

type Stats = {
  total_printers?: number;
  online_printers?: number;
  offline_printers?: number;
  total_events_today?: number;
  critical_events?: number;
  low_toner_count?: number;
};

type Charts = {
  by_type: { event_type: string; count: number }[];
  by_severity: { severity: string; count: number }[];
  timeline_24h: { hour: string; count: number }[];
  timeline_7d: { day: string; count: number }[];
  by_vendor: { vendor: string; count: number }[];
  top_printers: { printer_id: number; name: string; ip: string; location?: string; count: number }[];
  low_consumables: { printer_id: number; printer_name: string; ip: string; location?: string; name: string; level: number }[];
  online_offline: { label: string; count: number }[];
};

const VENDOR_COLORS = ['#5B8DEF', '#F6AD55', '#48BB78', '#ED64A6', '#9F7AEA', '#38B2AC', '#F56565', '#A0AEC0'];
const ONOFF_COLORS = ['#38A169', '#A0AEC0'];

const colorOfConsumable = (name: string): string => {
  const n = name.toLowerCase();
  if (n.includes('black')) return '#1a202c';
  if (n.includes('cyan')) return '#00B0E0';
  if (n.includes('magenta')) return '#D9006C';
  if (n.includes('yellow')) return '#F7D000';
  if (n.includes('drum')) return '#7B5BAA';
  if (n.includes('fuser')) return '#C2410C';
  return '#718096';
};

const StatCard = ({
  icon, label, value, color,
}: { icon: any; label: string; value: number | string; color: string }) => (
  <Paper sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2, height: '100%' }}>
    <Avatar sx={{ bgcolor: color, width: 56, height: 56 }}>{icon}</Avatar>
    <Box>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h3" sx={{ fontWeight: 600, lineHeight: 1 }}>{value}</Typography>
    </Box>
  </Paper>
);

export default function Dashboard() {
  const { t, lang } = useT();
  const [stats, setStats] = useState<Stats | null>(null);
  const [charts, setCharts] = useState<Charts | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = () => {
    Promise.all([
      api.get('/statistics').then((r) => r.data).catch(() => ({})),
      api.get('/statistics/charts').then((r) => r.data).catch(() => null),
    ]).then(([s, c]) => {
      setStats(s);
      // Localise online/offline labels in pie data
      if (c?.online_offline) {
        c.online_offline = [
          { label: t('dashboard.online'), count: c.online_offline[0]?.count ?? 0 },
          { label: t('dashboard.offline'), count: c.online_offline[1]?.count ?? 0 },
        ];
      }
      setCharts(c);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
    const i = setInterval(reload, 30_000);
    return () => clearInterval(i);
  }, [lang]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;

  const s = stats || {};

  return (
    <Box>
      <Typography variant="h4" gutterBottom>{t('dashboard.title')}</Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard icon={<PrintIcon />} label={t('dashboard.total')} value={s.total_printers ?? 0} color="#3182CE" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard icon={<CloudDoneIcon />} label={t('dashboard.online')} value={s.online_printers ?? 0} color="#38A169" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard icon={<CloudOffIcon />} label={t('dashboard.offline')} value={s.offline_printers ?? 0} color="#A0AEC0" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard icon={<ErrorIcon />} label={t('dashboard.errors_today')} value={s.total_events_today ?? 0} color="#E53E3E" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 6 }}>
          <StatCard icon={<InvertColorsIcon />} label={t('dashboard.low_consumables')} value={s.low_toner_count ?? 0} color="#DD6B20" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 6 }}>
          <StatCard icon={<ErrorIcon />} label={t('dashboard.critical_events')} value={s.critical_events ?? 0} color="#9B2C2C" />
        </Grid>
      </Grid>

      {charts && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.events_24h')}</Typography>
              <Box sx={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={charts.timeline_24h}>
                    <defs>
                      <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3182CE" stopOpacity={0.7} />
                        <stop offset="100%" stopColor="#3182CE" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="count" stroke="#3182CE" fill="url(#g1)" name={t('dashboard.events_label')} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 4 }}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.state')}</Typography>
              <Box sx={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={charts.online_offline}
                      dataKey="count" nameKey="label"
                      cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                      label={(e) => `${e.label}: ${e.count}`}
                    >
                      {charts.online_offline.map((_, i) => (
                        <Cell key={i} fill={ONOFF_COLORS[i]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.by_type')}</Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={charts.by_type} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                    <YAxis type="category" dataKey="event_type" tick={{ fontSize: 12 }} width={130} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#DD6B20" />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.by_vendor')}</Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={charts.by_vendor}
                      dataKey="count" nameKey="vendor"
                      cx="50%" cy="50%" outerRadius={110}
                      label={(e) => `${e.vendor}: ${e.count}`}
                    >
                      {charts.by_vendor.map((_, i) => (
                        <Cell key={i} fill={VENDOR_COLORS[i % VENDOR_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.events_7d')}</Typography>
              <Box sx={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={charts.timeline_7d}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#805AD5" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.top_printers')}</Typography>
              {charts.top_printers.length === 0 ? (
                <Typography color="text.secondary" sx={{ p: 2 }}>{t('dashboard.no_events_24h')}</Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('col.printer')}</TableCell>
                      <TableCell>{t('col.ip')}</TableCell>
                      <TableCell>{t('col.location')}</TableCell>
                      <TableCell align="right">{t('col.events_count')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {charts.top_printers.map((p) => (
                      <TableRow key={p.printer_id}>
                        <TableCell>{p.name}</TableCell>
                        <TableCell>{p.ip}</TableCell>
                        <TableCell>{p.location || '—'}</TableCell>
                        <TableCell align="right"><Chip label={p.count} size="small" color="error" /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid>

          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>{t('dashboard.chart.low_consumables')}</Typography>
              {charts.low_consumables.length === 0 ? (
                <Typography color="text.secondary" sx={{ p: 2 }}>{t('dashboard.consumables_ok')}</Typography>
              ) : (
                <Stack spacing={1}>
                  {charts.low_consumables.map((c, i) => (
                    <Box key={i} sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 2fr 80px', gap: 2, alignItems: 'center', py: 0.5 }}>
                      <Typography variant="body2"><strong>{c.printer_name}</strong></Typography>
                      <Typography variant="body2" color="text.secondary">{c.ip}</Typography>
                      <Typography variant="body2">{c.location || '—'}</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" sx={{ minWidth: 70 }}>{c.name}</Typography>
                        <LinearProgress
                          variant="determinate"
                          value={Math.max(0, Math.min(100, c.level))}
                          sx={{
                            flexGrow: 1, height: 10, borderRadius: 5,
                            backgroundColor: '#3333',
                            '& .MuiLinearProgress-bar': { backgroundColor: colorOfConsumable(c.name) },
                          }}
                        />
                      </Box>
                      <Chip label={`${c.level}%`} size="small" color={c.level <= 5 ? 'error' : 'warning'} />
                    </Box>
                  ))}
                </Stack>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
