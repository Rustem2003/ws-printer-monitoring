import { useState } from 'react';
import { Box, Typography, Link, IconButton, Tooltip, Stack, Divider } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import FavoriteIcon from '@mui/icons-material/Favorite';
import EmailIcon from '@mui/icons-material/Email';
import { useT } from '../i18n';

const IBAN = 'KZ48722S000035656178';
const COMPANY = 'ИП WEB-Soft';
const EMAIL = 'info@web-soft.kz';

export default function Footer() {
  const { t } = useT();
  const [copied, setCopied] = useState(false);

  const copyIban = async () => {
    try {
      await navigator.clipboard.writeText(IBAN);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {}
  };

  return (
    <Box
      component="footer"
      sx={{
        mt: 6, pt: 3, pb: 3,
        borderTop: 1, borderColor: 'divider',
        textAlign: 'center',
        color: 'text.secondary',
      }}
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={{ xs: 1.5, md: 4 }}
        divider={<Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', md: 'block' } }} />}
        alignItems="center"
        justifyContent="center"
      >
        <Typography variant="body2">
          <strong>{t('footer.developed_by')}:</strong>{' '}
          <Box component="span" sx={{ color: 'text.primary' }}>{COMPANY}</Box>
        </Typography>

        <Typography variant="body2" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
          <EmailIcon fontSize="small" />
          <strong>{t('footer.contact')}:</strong>{' '}
          <Link href={`mailto:${EMAIL}`} underline="hover">{EMAIL}</Link>
        </Typography>

        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
          <FavoriteIcon fontSize="small" sx={{ color: '#E53E3E' }} />
          <Typography variant="body2" component="span">
            {t('footer.support_intro')}{' '}
            <Box component="span" sx={{ fontFamily: 'monospace', fontWeight: 600, color: 'text.primary' }}>
              {IBAN}
            </Box>
          </Typography>
          <Tooltip title={copied ? t('footer.copied') : t('footer.copy')}>
            <IconButton size="small" onClick={copyIban} color={copied ? 'success' : 'default'}>
              {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
        </Box>
      </Stack>
    </Box>
  );
}
