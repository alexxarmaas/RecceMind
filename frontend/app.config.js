const googleMapsApiKey = process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || '';

module.exports = {
  expo: {
    name: 'RecceMind',
    slug: 'reccemind',
    version: '0.2.0',
    orientation: 'portrait',
    icon: './assets/logoRecce.png',
    userInterfaceStyle: 'dark',
    splash: {
      image: './assets/logoRecce.png',
      resizeMode: 'contain',
      backgroundColor: '#000000',
    },
    ios: {
      supportsTablet: true,
      bundleIdentifier: 'com.alexxarmaas.reccemind',
      config: {
        googleMapsApiKey,
      },
    },
    android: {
      package: 'com.alexxarmaas.reccemind',
      predictiveBackGestureEnabled: false,
      config: {
        googleMaps: {
          apiKey: googleMapsApiKey,
        },
      },
      adaptiveIcon: {
        backgroundColor: '#000000',
        foregroundImage: './assets/logoRecce.png',
        backgroundImage: './assets/android-icon-background.png',
        monochromeImage: './assets/android-icon-monochrome.png',
      },
    },
    web: {
      favicon: './assets/logoRecce.png',
    },
    extra: {
      googleMapsApiKey,
    },
    plugins: ['expo-font'],
  },
};
