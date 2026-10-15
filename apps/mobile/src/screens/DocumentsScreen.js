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
} from 'react-native';
import { Card, Title, Paragraph, Searchbar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useApi } from '../context/ApiContext';

const DocumentsScreen = ({ navigation }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { getDocuments } = useApi();

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.items || []);
    } catch (error) {
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDocuments();
    setRefreshing(false);
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
      <View style={styles.container}>
        <Text>Loading documents...</Text>
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
});

export default DocumentsScreen;