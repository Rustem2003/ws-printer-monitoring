import axios from 'axios';
import { API_BASE_URL } from './config';

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e?.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      if (location.pathname !== '/login') location.href = '/login';
    }
    return Promise.reject(e);
  },
);
