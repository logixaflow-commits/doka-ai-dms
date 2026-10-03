/**
 * API Context for making API calls
 */
import React, { createContext, useContext, useMemo } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const ApiContext = createContext(null);
const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export const ApiProvider = ({ children }) => {
  const { userToken } = useAuth();

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: { Accept: 'application/json' },
    });

    instance.interceptors.request.use((config) => {
      if (userToken) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${userToken}`;
      }
      return config;
    });

    return instance;
  }, [userToken]);

  const value = useMemo(() => ({
    api,
    getDocuments: async (params = {}) => {
      const response = await api.get('/documents', { params });
      return response.data;
    },
    uploadDocument: async (file) => {
      if (!file || !file.uri || !file.name || !file.type) {
        throw new Error('A valid local file URI, name and MIME type are required.');
      }

      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.type,
      });

      const response = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      return { success: true, data: response.data };
    },
    getDocument: async (documentId) => {
      const response = await api.get(`/documents/${documentId}`);
      return response.data;
    },
    deleteDocument: async (documentId) => {
      const response = await api.delete(`/documents/${documentId}`);
      return response.data;
    },
    searchDocuments: async (query, filters = {}) => {
      const response = await api.post('/search/advanced', { query, filters });
      return response.data;
    },
    getDashboardStats: async () => {
      const response = await api.get('/admin/analytics/dashboard');
      return response.data;
    },
  }), [api]);

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
};

export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within ApiProvider');
  }
  return context;
};
