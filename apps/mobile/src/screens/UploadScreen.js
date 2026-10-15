/**
 * Upload Screen
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Card, Title, Button } from 'react-native-paper';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useApi } from '../context/ApiContext';
const { normalizePickedFile } = require('../utils/uploadFile.cjs');

const UploadScreen = () => {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const { uploadDocument } = useApi();

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*'],
      });

      const file = normalizePickedFile(result);
      if (file) setSelectedFile(file);
    } catch (error) {
      Alert.alert('Error', 'Failed to pick document');
    }
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 1,
      });

      const file = normalizePickedFile(result, 'image/jpeg');
      if (file) setSelectedFile(file);
    } catch (error) {
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      Alert.alert('Error', 'Please select a file first');
      return;
    }

    setUploading(true);
    try {
      const result = await uploadDocument(selectedFile);
      
      if (result.success) {
        Alert.alert('Success', 'Document uploaded successfully');
        setSelectedFile(null);
      } else {
        Alert.alert('Error', result.error || 'Upload failed');
      }
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Upload Document</Text>
      
      <Card style={styles.card}>
        <Card.Content>
          <TouchableOpacity style={styles.uploadOption} onPress={pickDocument}>
            <Icon name="folder" size={40} color="#2196F3" />
            <Text style={styles.optionText}>Pick from Files</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.uploadOption} onPress={pickImage}>
            <Icon name="image" size={40} color="#2196F3" />
            <Text style={styles.optionText}>Pick from Gallery</Text>
          </TouchableOpacity>
        </Card.Content>
      </Card>

      {selectedFile && (
        <Card style={styles.card}>
          <Card.Content>
            <Title>Selected File</Title>
            <Text style={styles.fileName}>{selectedFile.name}</Text>
            <Text style={styles.fileSize}>
              {selectedFile.size !== null ? `${(selectedFile.size / 1024).toFixed(2)} KB` : 'Unknown size'}
            </Text>
            
            {uploading ? (
              <ActivityIndicator size="large" color="#2196F3" />
            ) : (
              <Button mode="contained" onPress={handleUpload} style={styles.uploadButton}>
                Upload Document
              </Button>
            )}
          </Card.Content>
        </Card>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#333',
  },
  card: {
    marginBottom: 20,
    elevation: 2,
  },
  uploadOption: {
    alignItems: 'center',
    padding: 20,
    marginBottom: 10,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  optionText: {
    fontSize: 16,
    marginTop: 10,
    color: '#333',
  },
  fileName: {
    fontSize: 16,
    marginTop: 10,
    color: '#333',
  },
  fileSize: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  uploadButton: {
    marginTop: 15,
  },
});

export default UploadScreen;