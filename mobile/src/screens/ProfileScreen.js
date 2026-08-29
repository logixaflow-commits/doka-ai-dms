/**
 * Profile Screen
 */
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { Card, Title, Paragraph, Button, Avatar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../context/AuthContext';

const ProfileScreen = () => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.card}>
        <Card.Content style={styles.profileHeader}>
          <Avatar.Text size={80} label={user?.username?.[0]?.toUpperCase() || 'U'} />
          <View style={styles.userInfo}>
            <Title style={styles.username}>{user?.username || 'User'}</Title>
            <Paragraph style={styles.email}>{user?.email || 'user@example.com'}</Paragraph>
            <Paragraph style={styles.role}>{user?.role || 'Staff'}</Paragraph>
          </View>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.infoRow}>
            <Icon name="person" size={24} color="#2196F3" />
            <View style={styles.infoText}>
              <Text style={styles.label}>Username</Text>
              <Text style={styles.value}>{user?.username || 'N/A'}</Text>
            </View>
          </View>
          
          <View style={styles.infoRow}>
            <Icon name="email" size={24} color="#2196F3" />
            <View style={styles.infoText}>
              <Text style={styles.label}>Email</Text>
              <Text style={styles.value}>{user?.email || 'N/A'}</Text>
            </View>
          </View>
          
          <View style={styles.infoRow}>
            <Icon name="badge" size={24} color="#2196F3" />
            <View style={styles.infoText}>
              <Text style={styles.label}>Role</Text>
              <Text style={styles.value}>{user?.role || 'N/A'}</Text>
            </View>
          </View>
          
          <View style={styles.infoRow}>
            <Icon name="calendar-today" size={24} color="#2196F3" />
            <View style={styles.infoText}>
              <Text style={styles.label}>Member Since</Text>
              <Text style={styles.value}>
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      <Button mode="contained" onPress={handleLogout} style={styles.logoutButton}>
        Logout
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
  profileHeader: {
    alignItems: 'center',
    padding: 20,
  },
  userInfo: {
    alignItems: 'center',
    marginTop: 15,
  },
  username: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  email: {
    fontSize: 16,
    color: '#666',
    marginTop: 5,
  },
  role: {
    fontSize: 14,
    color: '#2196F3',
    marginTop: 5,
    textTransform: 'capitalize',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  infoText: {
    marginLeft: 15,
    flex: 1,
  },
  label: {
    fontSize: 12,
    color: '#666',
  },
  value: {
    fontSize: 16,
    color: '#333',
    marginTop: 2,
  },
  logoutButton: {
    marginTop: 20,
    backgroundColor: '#f44336',
  },
});

export default ProfileScreen;