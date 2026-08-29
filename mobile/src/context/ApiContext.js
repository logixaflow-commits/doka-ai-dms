/**
 * API Context for making API calls
 */
import React, { createContext, useContext } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const ApiContext = createContext(null);

const API_BASE_URL = 'http://localhost:8000/api';

export const ApiProvider = ({ children }) => {
  const { userToken } = useAuth();

  const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Add auth token to requests
  api.interceptors.request.use(
    (config) => {
      if (userToken) {
        config.headers.Authorization = `Bearer ${userToken}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // API Methods
  const getDocuments = async (params = {}) => {
    try {
      const response = await api.get('/documents', { params });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const uploadDocument = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const getDocument = async (documentId) => {
    try {
      const response = await api.get(`/documents/${documentId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const deleteDocument = async (documentId) => {
    try {
      const response = await api.delete(`/documents/${documentId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const searchDocuments = async (query, filters = {}) => {
    try {
      const response = await api.post('/search/advanced', {
        query,
        filters,
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const getDashboardStats = async () => {
    try {
      const response = await api.get('/admin/analytics/dashboard');
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  return (
    <ApiContext.Provider
      value={{
        api,
        getDocuments,
        uploadDocument,
        getDocument,
        deleteDocument,
        searchDocuments,
        getDashboardStats,
      }}
    >
      {children}
    </ApiContext.Provider>
  );
};

export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within ApiProvider');
  }
  return context;
};