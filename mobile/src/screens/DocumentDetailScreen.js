/**
 * Document Detail Screen
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { Card, Title, Paragraph, Button, Chip } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useApi } from '../context/ApiContext';

const DocumentDetailScreen = ({ route, navigation }) => {
  const { documentId } = route.params;
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const { getDocument, deleteDocument } = useApi();

  useEffect(() => {
    loadDocument();
  }, [documentId]);

  const loadDocument = async () => {
    try {
      const data = await getDocument(documentId);
      setDocument(data);
    } catch (error) {
      Alert.alert('Error', 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    Alert.alert(
      'Delete Document',
      'Are you sure you want to delete this document?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteDocument(documentId);
              Alert.alert('Success', 'Document deleted successfully');
              navigation.goBack();
            } catch (error) {
              Alert.alert('Error', 'Failed to delete document');
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text>Loading...</Text>
      </View>
    );
  }

  if (!document) {
    return (
      <View style={styles.container}>
        <Text>Document not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.header}>
            <Icon name="description" size={32} color="#2196F3" />
            <Title style={styles.title}>{document.original_filename}</Title>
          </View>
          
          <Chip mode="flat" style={styles.chip}>
            {document.status}
          </Chip>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Title>Document Information</Title>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>Category:</Text>
            <Text style={styles.value}>{document.category || 'Uncategorized'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>Function Type:</Text>
            <Text style={styles.value}>{document.function_type || 'Unknown'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>Quality Level:</Text>
            <Text style={styles.value}>{document.quality_level || 'Unknown'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>File Size:</Text>
            <Text style={styles.value}>{document.file_size ? `${(document.file_size / 1024).toFixed(2)} KB` : 'Unknown'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>MIME Type:</Text>
            <Text style={styles.value}>{document.mime_type || 'Unknown'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>Created At:</Text>
            <Text style={styles.value}>
              {document.created_at ? new Date(document.created_at).toLocaleString() : 'Unknown'}
            </Text>
          </View>
        </Card.Content>
      </Card>

      {document.extracted_metadata && Object.keys(document.extracted_metadata).length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Title>Extracted Metadata</Title>
            {Object.entries(document.extracted_metadata).map(([key, value]) => (
              <View key={key} style={styles.infoRow}>
                <Text style={styles.label}>{key}:</Text>
                <Text style={styles.value}>{String(value)}</Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      <Button mode="contained" onPress={handleDelete} style={styles.deleteButton} buttonColor="#f44336">
        Delete Document
      </Button>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  card: {
    marginBottom: 20,
    elevation: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  title: {
    fontSize: 18,
    marginLeft: 10,
    flex: 1,
  },
  chip: {
    alignSelf: 'flex-start',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  label: {
    fontSize: 14,
    color: '#666',
    fontWeight: 'bold',
  },
  value: {
    fontSize: 14,
    color: '#333',
  },
  deleteButton: {
    marginTop: 10,
  },
});

export default DocumentDetailScreen;