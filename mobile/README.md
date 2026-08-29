# Enterprise AI DMS - Mobile Application

React Native mobile application for Enterprise AI Document Management System.

## Features

- **Authentication**: Secure login with JWT tokens
- **Dashboard**: Overview of document statistics
- **Document Management**: View, search, and manage documents
- **Document Upload**: Upload documents from device files or camera
- **Document Details**: View detailed document information
- **User Profile**: View and manage user profile
- **Offline Support**: Local storage for offline access
- **Push Notifications**: Real-time notifications (optional)

## Technology Stack

- **Framework**: React Native with Expo
- **Navigation**: React Navigation
- **State Management**: React Context API
- **UI Components**: React Native Paper
- **HTTP Client**: Axios
- **Secure Storage**: Expo SecureStore
- **File Picker**: Expo Document Picker & Image Picker

## Installation

```bash
cd mobile
npm install
```

## Running the App

### Start Development Server
```bash
npm start
```

### Run on iOS
```bash
npm run ios
```

### Run on Android
```bash
npm run android
```

### Run on Web
```bash
npm run web
```

## Configuration

### API Base URL
Update the API base URL in `src/context/ApiContext.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

For production, update to your production API URL.

## Project Structure

```
mobile/
├── App.js                          # Main app component
├── package.json                    # Dependencies
├── babel.config.js                 # Babel configuration
├── src/
│   ├── context/
│   │   ├── AuthContext.js         # Authentication context
│   │   └── ApiContext.js          # API context
│   └── screens/
│       ├── LoginScreen.js         # Login screen
│       ├── DashboardScreen.js     # Dashboard screen
│       ├── DocumentsScreen.js     # Documents list screen
│       ├── UploadScreen.js        # Document upload screen
│       ├── ProfileScreen.js       # User profile screen
│       └── DocumentDetailScreen.js # Document detail screen
```

## Screens

### Login Screen
- Username/password authentication
- Secure token storage
- Error handling

### Dashboard Screen
- Document statistics
- Recent activity
- Quick actions

### Documents Screen
- Document list with filtering
- Search functionality
- Pull-to-refresh
- Document status indicators

### Upload Screen
- File picker integration
- Camera integration
- Upload progress
- Error handling

### Profile Screen
- User information display
- Logout functionality
- Account settings

### Document Detail Screen
- Document metadata
- Version history
- Document actions (delete, share)

## API Integration

The mobile app uses the same API as the web application:
- Authentication endpoints
- Document CRUD operations
- Search and filtering
- File upload/download

## Security

- JWT token authentication
- Secure storage for tokens
- HTTPS for production
- Biometric authentication (optional)

## Deployment

### Build for iOS
```bash
eas build --platform ios
```

### Build for Android
```bash
eas build --platform android
```

### Submit to App Stores
```bash
eas submit --platform ios
eas submit --platform android
```

## Future Enhancements

- Offline document viewing
- Biometric authentication
- Push notifications
- Document annotation
- Real-time collaboration
- Advanced search filters
- Custom themes

## Troubleshooting

### Metro bundler issues
```bash
npx react-native start --reset-cache
```

### iOS build issues
```bash
cd ios && pod install
```

### API connection issues
- Ensure backend server is running
- Check API base URL configuration
- Verify network connectivity

## Development Notes

- The app uses Expo for development
- For production, consider ejecting to native code
- Test on both iOS and Android devices
- Use emulator for quick testing