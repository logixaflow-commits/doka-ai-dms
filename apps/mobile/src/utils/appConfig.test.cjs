const test = require("node:test");
const assert = require("node:assert/strict");
const appConfig = require("../../app.json");

test("declares purpose-specific iOS camera and photo-library permissions", () => {
  const info = appConfig.expo.ios.infoPlist;
  assert.match(info.NSCameraUsageDescription, /capture a document/i);
  assert.match(info.NSPhotoLibraryUsageDescription, /choose an image to upload/i);
});

test("declares the Android camera and image permission set", () => {
  assert.ok(appConfig.expo.android.permissions.includes("CAMERA"));
  assert.ok(appConfig.expo.android.permissions.includes("READ_MEDIA_IMAGES"));
});

test("Expo image picker plugins carry user-facing permission explanations", () => {
  const plugins = appConfig.expo.plugins;
  const imagePicker = plugins.find((entry) => Array.isArray(entry) && entry[0] === "expo-image-picker");
  const camera = plugins.find((entry) => Array.isArray(entry) && entry[0] === "expo-camera");
  assert.ok(imagePicker?.[1]?.photosPermission);
  assert.ok(imagePicker?.[1]?.cameraPermission);
  assert.ok(camera?.[1]?.cameraPermission);
});
