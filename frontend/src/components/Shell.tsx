import { ReactNode, useState, MouseEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, IconButton, Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Menu, MenuItem, Button,
} from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import LanguageIcon from '@mui/icons-material/Language';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PrintIcon from '@mui/icons-material/Print';
import EventIcon from '@mui/icons-material/Event';
import TelegramIcon from '@mui/icons-material/Telegram';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useAuth } from '../auth';
import { useT, Lang, LANG_LABELS } from '../i18n';
import Footer from './Footer';

const drawerWidth = 240;

export default function Shell({
  children,
  toggleTheme,
  mode,
}: {
  children: ReactNode;
  toggleTheme: () => void;
  mode: 'dark' | 'light';
}) {
  const auth = useAuth();
  const navTo = useNavigate();
  const loc = useLocation();
  const { t, lang, setLang } = useT();
  const [langAnchor, setLangAnchor] = useState<HTMLElement | null>(null);

  const nav = [
    { to: '/', label: t('nav.dashboard'), icon: <DashboardIcon /> },
    { to: '/printers', label: t('nav.printers'), icon: <PrintIcon /> },
    { to: '/events', label: t('nav.events'), icon: <EventIcon /> },
    { to: '/telegram', label: t('nav.telegram'), icon: <TelegramIcon /> },
    { to: '/notification-settings', label: t('nav.notification_settings'), icon: <NotificationsActiveIcon /> },
    { to: '/bot-settings', label: t('nav.bot_settings'), icon: <SmartToyIcon /> },
  ];

  const logout = () => {
    auth.clear();
    navTo('/login');
  };

  const openLang = (e: MouseEvent<HTMLElement>) => setLangAnchor(e.currentTarget);
  const closeLang = () => setLangAnchor(null);
  const pickLang = (l: Lang) => { setLang(l); closeLang(); };

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (th) => th.zIndex.drawer + 1 }}>
        <Toolbar>
          <Box
            component="img"
            src="/logo.svg"
            alt="WS"
            sx={{ width: 36, height: 36, mr: 1.5, borderRadius: 1 }}
          />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700, letterSpacing: 0.3 }}>
            {t('app.title')}
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>{auth.username}</Typography>
          <Button
            color="inherit"
            startIcon={<LanguageIcon />}
            onClick={openLang}
            sx={{ textTransform: 'none', mr: 1 }}
            title={t('shell.language')}
          >
            {lang.toUpperCase()}
          </Button>
          <Menu anchorEl={langAnchor} open={!!langAnchor} onClose={closeLang}>
            {(['ru', 'kk', 'en'] as Lang[]).map((l) => (
              <MenuItem key={l} selected={l === lang} onClick={() => pickLang(l)}>
                <strong style={{ marginRight: 8 }}>{l.toUpperCase()}</strong> {LANG_LABELS[l]}
              </MenuItem>
            ))}
          </Menu>
          <IconButton color="inherit" onClick={toggleTheme}
            title={mode === 'dark' ? t('shell.theme.light') : t('shell.theme.dark')}>
            {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
          <IconButton color="inherit" onClick={logout} title={t('shell.logout')}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{ width: drawerWidth, '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' } }}
      >
        <Toolbar />
        <List>
          {nav.map((n) => (
            <ListItemButton key={n.to} component={Link} to={n.to} selected={loc.pathname === n.to}>
              <ListItemIcon>{n.icon}</ListItemIcon>
              <ListItemText primary={n.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Toolbar />
        <Box sx={{ flexGrow: 1 }}>{children}</Box>
        <Footer />
      </Box>
    </Box>
  );
}
