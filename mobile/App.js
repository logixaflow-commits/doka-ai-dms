/**
 * Main App Component for Enterprise AI DMS Mobile
 */
import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';
import { PaperProvider } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Screens
import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import DocumentsScreen from './src/screens/DocumentsScreen';
import UploadScreen from './src/screens/UploadScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import DocumentDetailScreen from './src/screens/DocumentDetailScreen';

// Context
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ApiProvider } from './src/context/ApiContext';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

// Auth Stack
function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
    </Stack.Navigator>
  );
}

// Main Tab Navigator
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          if (route.name === 'Dashboard') {
            iconName = 'dashboard';
          } else if (route.name === 'Documents') {
            iconName = 'folder';
          } else if (route.name === 'Upload') {
            iconName = 'cloud-upload';
          } else if (route.name === 'Profile') {
            iconName = 'person';
          }
          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: 'gray',
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Documents" component={DocumentsScreen} />
      <Tab.Screen name="Upload" component={UploadScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

// Document Stack
function DocumentStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="Documents" component={DocumentsScreen} />
      <Stack.Screen name="DocumentDetail" component={DocumentDetailScreen} />
    </Stack.Navigator>
  );
}

// Root Navigator
function RootNavigator() {
  const { userToken } = useAuth();
  
  return (
    <NavigationContainer>
      {userToken ? (
        <Stack.Navigator>
          <Stack.Screen 
            name="MainTabs" 
            component={MainTabs} 
            options={{ headerShown: false }}
          />
          <Stack.Screen 
            name="DocumentStack" 
            component={DocumentStack}
            options={{ title: 'Documents' }}
          />
        </Stack.Navigator>
      ) : (
        <AuthStack />
      )}
    </NavigationContainer>
  );
}

// Main App
export default function App() {
  return (
    <AuthProvider>
      <ApiProvider>
        <PaperProvider>
          <StatusBar style="auto" />
          <RootNavigator />
        </PaperProvider>
      </ApiProvider>
    </AuthProvider>
  );
}