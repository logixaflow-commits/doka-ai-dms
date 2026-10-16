/**
 * Documents Screen
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { Card, Title, Paragraph, Searchbar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useApi } from '../context/ApiContext';

const DocumentsScreen = ({ navigation }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState(null);
  const { getDocuments } = useApi();

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data.items || []);
    } catch (err) {
      console.error('Error loading documents:', err);
      setError(err?.message || 'Failed to load documents. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocuments(data.items || []);
    } catch (err) {
      console.error('Error refreshing documents:', err);
      setError(err?.message || 'Failed to refresh documents.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleDocumentPress = (document) => {
    navigation.navigate('DocumentDetail', { documentId: document.id });
  };

  const filteredDocuments = documents.filter(doc =>
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const renderDocument = ({ item }) => (
    <TouchableOpacity onPress={() => handleDocumentPress(item)}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.cardHeader}>
            <View style={styles.cardTitle}>
              <Icon name="description" size={24} color="#2196F3" />
              <Title style={styles.title}>{item.original_filename}</Title>
            </View>
            <Text style={[
              styles.status,
              { color: item.status === 'approved' ? '#4CAF50' : '#FF9800' }
            ]}>
              {item.status}
            </Text>
          </View>
          <Paragraph style={styles.paragraph}>
            Category: {item.category || 'Uncategorized'}
          </Paragraph>
          <Paragraph style={styles.paragraph}>
            Function: {item.function_type || 'Unknown'}
          </Paragraph>
          <Paragraph style={styles.paragraph}>
            Quality: {item.quality_level || 'Unknown'}
          </Paragraph>
        </Card.Content>
      </Card>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading documents...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>Something went wrong</Text>
        <Text style={styles.errorMessage}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadDocuments}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Searchbar
        placeholder="Search documents..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={styles.searchbar}
      />
      <FlatList
        data={filteredDocuments}
        renderItem={renderDocument}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📄</Text>
            <Text style={styles.emptyTitle}>No documents found</Text>
            <Text style={styles.emptyMessage}>
              {searchQuery ? 'Try a different search term.' : 'Upload your first document to get started.'}
            </Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchbar: {
    margin: 15,
    elevation: 2,
  },
  list: {
    padding: 15,
    flexGrow: 1,
  },
  card: {
    marginBottom: 15,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  title: {
    fontSize: 16,
    marginLeft: 10,
  },
  status: {
    fontSize: 12,
    fontWeight: 'bold',
    textTransform: 'capitalize',
  },
  paragraph: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  emptyMessage: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    lineHeight: 20,
  },
});

export default DocumentsScreen;