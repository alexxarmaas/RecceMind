import React, { useState, useRef, useEffect } from 'react';
import { View, StyleSheet, TextInput, ActivityIndicator, Alert, Text, Dimensions, Image, TouchableOpacity, KeyboardAvoidingView, Platform, Modal, Button, ScrollView, Linking, LayoutAnimation, UIManager } from 'react-native';
import MapView, { Polyline, Marker, Callout } from 'react-native-maps';
import { BlurView } from 'expo-blur';
import { FontAwesome5 } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import * as Print from 'expo-print';
import * as Speech from 'expo-speech';
import ViewShot from 'react-native-view-shot';
import * as DocumentPicker from 'expo-document-picker';
import { WebView } from 'react-native-webview';
import { Audio } from 'expo-av';
import * as Location from 'expo-location';
import { analyzeRoute, processGpx, submitFeedback, transcribeAudio, processCoords, processTelemetry } from '../services/apiService';
import PacenoteList from '../components/PacenoteList';
import { darkMapStyle } from '../utils/mapStyle';

const { height } = Dimensions.get('window');

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const MapScreen = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [loading, setLoading] = useState(false);
  const [routeData, setRouteData] = useState<any>(null);
  const [selectedCurveIndex, setSelectedCurveIndex] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [streetViewCoord, setStreetViewCoord] = useState<{lat: number, lng: number} | null>(null);
  const [thresholds, setThresholds] = useState({ "6": "150", "5": "100", "4": "60", "3": "35", "2": "20" });
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isRecceMode, setIsRecceMode] = useState(false);
  const [recceCoords, setRecceCoords] = useState<{latitude: number, longitude: number}[]>([]);
  const [driverId, setDriverId] = useState("default");
  const [showTelemetry, setShowTelemetry] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIndexRef = useRef(0);
  const locationSubRef = useRef<Location.LocationSubscription | null>(null);
  const mapRef = useRef<MapView>(null);
  const viewShotRef = useRef<ViewShot>(null);

  // Simple decoder for the encoded polyline
  const decodePolyline = (encoded: string) => {
    let points = [];
    let index = 0, len = encoded.length;
    let lat = 0, lng = 0;

    while (index < len) {
      let b, shift = 0, result = 0;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      let dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lat += dlat;

      shift = 0;
      result = 0;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      let dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lng += dlng;

      points.push({ latitude: (lat / 1e5), longitude: (lng / 1e5) });
    }
    return points;
  };

  const handleGenerate = async () => {
    if (!origin || !destination) {
      Alert.alert('Error', 'Por favor ingresa origen y destino.');
      return;
    }

    setLoading(true);
    try {
      const numericThresholds = {
        "6": parseInt(thresholds["6"]),
        "5": parseInt(thresholds["5"]),
        "4": parseInt(thresholds["4"]),
        "3": parseInt(thresholds["3"]),
        "2": parseInt(thresholds["2"])
      };
      const data = await analyzeRoute(origin, destination, numericThresholds, driverId);
      const points = decodePolyline(data.polyline);
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      setRouteData({ ...data, points });
    } catch (error) {
      Alert.alert('Error', 'No se pudo generar la ruta. Verifica que el backend esté en ejecución y la API Key de Google Maps sea válida.');
    } finally {
      setLoading(false);
    }
  };

  const handleNotePress = (curveIndex: number) => {
    setSelectedCurveIndex(curveIndex);
    if (routeData && routeData.curves && routeData.curves[curveIndex] && mapRef.current) {
      const curve = routeData.curves[curveIndex];
      const midIdx = Math.floor((curve.start_idx + curve.end_idx) / 2);
      const midPoint = routeData.points[midIdx];
      if (midPoint) {
        mapRef.current.animateToRegion({
          ...midPoint,
          latitudeDelta: 0.005,
          longitudeDelta: 0.005,
        }, 1000);
      }
    }
  };

  const handleNoteEdit = async (index: number, newNoteStr: string) => {
    if (!routeData) return;
    const notes = [...routeData.pacenotes];
    const oldNote = notes[index];
    notes[index] = { ...oldNote, text: newNoteStr };
    setRouteData({ ...routeData, pacenotes: notes });
    
    // Parse the new note string for ML feedback
    const oldMatch = oldNote.text.match(/(Izquierda|Derecha)\s(\d)/i);
    const newMatch = newNoteStr.match(/(Izquierda|Derecha)\s(\d)/i);
    
    if (oldMatch && newMatch && oldNote.curve_index !== null) {
       const curve = routeData.curves[oldNote.curve_index];
       if (curve) {
          try {
             await submitFeedback(
                curve.radius,
                curve.heading_change,
                curve.length,
                parseInt(oldMatch[2]),
                parseInt(newMatch[2]),
                driverId
             );
             Alert.alert("¡Cerebro Actualizado!", "La IA ha aprendido de tu corrección.");
          } catch (e) {
             console.error("Error submitting feedback", e);
          }
       }
    }
  };

  const handleExport = () => {
    if (!routeData || !routeData.pacenotes) {
      Alert.alert('Error', 'No hay notas para exportar.');
      return;
    }
    setShowExportModal(true);
  };

  const captureAndShare = async () => {
    try {
      const htmlContent = `
        <html>
          <head>
            <style>
              body { font-family: 'Helvetica', sans-serif; background-color: #ffffff; color: #000; padding: 20px; }
              h1 { color: #d60000; text-align: center; text-transform: uppercase; }
              table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 24px; }
              th, td { border: 2px solid #000; padding: 15px; text-align: left; font-weight: bold; }
              .dist-row { background-color: #f0f0f0; }
              .dist-cell { text-align: center; color: #666; font-size: 20px; }
              .icon-cell { width: 50px; text-align: center; font-size: 32px; color: #d60000; }
              .text-cell { text-transform: uppercase; }
            </style>
          </head>
          <body>
            <h1>Notas - RecceMind V5</h1>
            <h2>Piloto: ${driverId}</h2>
            <table>
              ${routeData?.pacenotes?.map((note: any) => {
                if (note.type === 'distance') {
                  return `<tr class="dist-row"><td colspan="2" class="dist-cell">${note.text} m</td></tr>`;
                }
                const isRight = note.text.toLowerCase().includes('derecha');
                const isLeft = note.text.toLowerCase().includes('izquierda');
                const isCrest = note.text.toLowerCase().includes('rasante') || note.text.toLowerCase().includes('salto');
                const icon = isCrest ? '⛰️' : (isRight ? '➔' : (isLeft ? '➔' : '↑'));
                const iconRot = isLeft ? 'display:inline-block; transform: scaleX(-1);' : '';
                return `<tr class="note-row"><td class="icon-cell"><span style="${iconRot}">${icon}</span></td><td class="text-cell">${note.text}</td></tr>`;
              }).join('')}
            </table>
          </body>
        </html>
      `;

      if (Platform.OS === 'web') {
        // En Web expo-print suele imprimir toda la pantalla (incluyendo la UI). 
        // Para imprimir solo el HTML puro abrimos una pestaña invisible/nueva y la imprimimos.
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(htmlContent);
          printWindow.document.close();
          printWindow.focus();
          setTimeout(() => {
            printWindow.print();
          }, 250);
        }
      } else {
        // En móvil generamos PDF y lo compartimos
        const { uri } = await Print.printToFileAsync({ html: htmlContent });
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(uri, { UTI: '.pdf', mimeType: 'application/pdf' });
        } else {
          Alert.alert('PDF Generado', `El PDF se guardó en: ${uri}`);
        }
      }
    } catch (e) {
      Alert.alert('Error', 'No se pudo exportar el PDF.');
    }
  };

  const exportSimulatorCSV = async () => {
    if (!routeData || !routeData.pacenotes) return;
    try {
      let csvContent = 'Distancia,Nota\n';
      let currentDistance = 0;
      
      routeData.pacenotes.forEach((note: any) => {
        if (note.type === 'distance') {
          currentDistance = parseInt(note.text);
        } else {
          csvContent += `${currentDistance},${note.text}\n`;
        }
      });

      if (Platform.OS === 'web') {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'pacenotes_sim.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        const fileUri = FileSystem.cacheDirectory + 'pacenotes_sim.csv';
        await FileSystem.writeAsStringAsync(fileUri, csvContent, { encoding: FileSystem.EncodingType.UTF8 });
        await Sharing.shareAsync(fileUri, { mimeType: 'text/csv', UTI: 'public.comma-separated-values-text' });
      }
    } catch (e) {
      Alert.alert('Error', 'No se pudo exportar el archivo CSV.');
    }
  };

  const handlePlaySimulation = () => {
    if (!routeData || !routeData.pacenotes || routeData.pacenotes.length === 0) return;
    setIsPlaying(true);
    playIndexRef.current = 0;
    
    const playNextNote = () => {
      // In React state closures might be tricky, so we rely on ref or just recursive timeouts
      // Actually, to read the latest state of isPlaying, we could use a ref. 
      // But let's just do it directly.
      if (playIndexRef.current >= routeData.pacenotes.length) {
        setIsPlaying(false);
        return;
      }
      
      const note = routeData.pacenotes[playIndexRef.current];
      let delayToNextMs = 2000;
      
      if (note.type === 'distance') {
        const dist = parseInt(note.text);
        // Average speed approx 25m/s (90km/h) for simulation
        delayToNextMs = (dist / 25) * 1000;
        Speech.speak(note.text, { rate: 1.2, language: 'es-ES' });
      } else {
        Speech.speak(note.text, { rate: 1.4, language: 'es-ES' });
        delayToNextMs = 1500;
      }
      
      playIndexRef.current++;
      // We don't check isPlaying here because setTimeout closure captures it wrongly if it changes,
      // We will check Speech.isSpeakingAsync() or just let it finish the sequence.
      // A better way to cancel is Speech.stop() and we can just use a global variable or ref for cancelling.
      setTimeout(() => {
         // if playIndexRef.current is -1, it means stopped
         if (playIndexRef.current !== -1) {
             playNextNote();
         }
      }, delayToNextMs);
    };
    
    playNextNote();
  };

  const handleStopSimulation = () => {
    setIsPlaying(false);
    playIndexRef.current = -1;
    Speech.stop();
  };

  const handleUploadGPX = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) return;

      const file = result.assets[0];
      setLoading(true);

      let gpxText = '';
      if (Platform.OS === 'web') {
        const response = await fetch(file.uri);
        gpxText = await response.text();
      } else {
        gpxText = await FileSystem.readAsStringAsync(file.uri);
      }

      const numericThresholds = {
        "6": parseInt(thresholds["6"]),
        "5": parseInt(thresholds["5"]),
        "4": parseInt(thresholds["4"]),
        "3": parseInt(thresholds["3"]),
        "2": parseInt(thresholds["2"])
      };
      
      const data = await processGpx(gpxText, numericThresholds, driverId);
      const points = decodePolyline(data.polyline);
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      setRouteData({ ...data, points });
      setOrigin('Archivo GPX');
      setDestination('');

    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'No se pudo procesar el archivo GPX. Asegúrate de que sea válido.');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadTelemetry = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['text/csv', 'application/vnd.ms-excel'],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) return;

      const fileAsset = result.assets[0];
      setLoading(true);

      const numericThresholds = {
        "6": parseInt(thresholds["6"]),
        "5": parseInt(thresholds["5"]),
        "4": parseInt(thresholds["4"]),
        "3": parseInt(thresholds["3"]),
        "2": parseInt(thresholds["2"])
      };
      
      let file: any;
      if (Platform.OS === 'web') {
        const response = await fetch(fileAsset.uri);
        const blob = await response.blob();
        file = new File([blob], fileAsset.name, { type: fileAsset.mimeType || 'text/csv' });
      } else {
        file = {
          uri: fileAsset.uri,
          name: fileAsset.name,
          type: 'text/csv',
        };
      }

      const data = await processTelemetry(file, numericThresholds, driverId);
      const points = decodePolyline(data.polyline);
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      setRouteData({ ...data, points });
      setOrigin('Archivo Telemetría');
      setDestination('');

    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'No se pudo procesar la telemetría. Verifica que sea un CSV válido (lat, lon, speed).');
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      if (Platform.OS === 'web') {
        Alert.alert('No soportado', 'La grabación de voz no está soportada en web todavía.');
        return;
      }
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording', err);
    }
  };

  const stopRecording = async () => {
    setIsRecording(false);
    if (!recording) return;
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (uri) {
        setLoading(true);
        const result = await transcribeAudio(uri);
        if (result.text && routeData) {
           const updatedNotes = [...routeData.pacenotes, { type: 'note', text: `🎙️ ${result.text}`, curve_index: null }];
           setRouteData({ ...routeData, pacenotes: updatedNotes });
           Alert.alert('Nota de voz', result.text);
        } else {
           Alert.alert('Voz no detectada', result.error || 'No se pudo transcribir el audio.');
        }
      }
    } catch (err) {
      console.error('Failed to stop recording', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleRecceMode = async () => {
    if (isRecceMode) {
      // Stop Recce Mode
      setIsRecceMode(false);
      if (locationSubRef.current) {
        locationSubRef.current.remove();
        locationSubRef.current = null;
      }
      if (recceCoords.length > 2) {
        setLoading(true);
        try {
          const numericThresholds = {
            "6": parseInt(thresholds["6"]),
            "5": parseInt(thresholds["5"]),
            "4": parseInt(thresholds["4"]),
            "3": parseInt(thresholds["3"]),
            "2": parseInt(thresholds["2"])
          };
          // Convert to [[lat, lon]]
          const coordsArray = recceCoords.map(c => [c.latitude, c.longitude]);
          const data = await processCoords(coordsArray, numericThresholds, driverId);
          const points = decodePolyline(data.polyline);
          setRouteData({ ...data, points });
          setOrigin('Reconocimiento GPS');
          setDestination('');
        } catch (e) {
          Alert.alert('Error', 'No se pudo procesar el tramo grabado.');
        } finally {
          setLoading(false);
        }
      }
    } else {
      // Start Recce Mode
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permiso denegado', 'Se necesita acceso a la ubicación para grabar el tramo.');
        return;
      }
      setRecceCoords([]);
      setRouteData(null);
      setIsRecceMode(true);
      locationSubRef.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 1000,
          distanceInterval: 5,
        },
        (loc) => {
          setRecceCoords(prev => [...prev, loc.coords]);
          mapRef.current?.animateToRegion({
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
          });
        }
      );
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <View style={styles.mapContainer}>
        <MapView
          ref={mapRef}
          style={styles.map}
          provider="google"
          customMapStyle={darkMapStyle}
          initialRegion={{
            latitude: 40.4168,
            longitude: -3.7038,
            latitudeDelta: 2.0,
            longitudeDelta: 2.0,
          }}
        >
          {routeData && routeData.points && (
            <Polyline
              coordinates={routeData.points}
              strokeColor={darkMapStyle.routeColor}
              strokeWidth={4}
            />
          )}
          {isRecceMode && recceCoords.length > 0 && (
            <Polyline
              coordinates={recceCoords}
              strokeColor="#ff0000"
              strokeWidth={4}
            />
          )}
          {routeData && routeData.curves && routeData.curves.map((curve: any, index: number) => {
            const curvePoints = routeData.points.slice(curve.start_idx, curve.end_idx + 1);
            const isSelected = selectedCurveIndex === index;
            const strokeColor = curve.direction === 'Derecha' ? '#d60000' : '#0000ff';
            
            // Calculate midpoint for marker
            const midIdx = Math.floor((curve.start_idx + curve.end_idx) / 2);
            const midPoint = routeData.points[midIdx];
            
            // Find the corresponding pacenote for this curve
            const pacenote = routeData.pacenotes.find((note: any) => note.curve_index === index);

            return (
              <React.Fragment key={`curve-${index}`}>
                <Polyline
                  coordinates={curvePoints}
                  strokeColor={isSelected ? '#FFD700' : strokeColor} // Yellow if selected
                  strokeWidth={isSelected ? 6 : 4}
                  zIndex={isSelected ? 10 : 5}
                />
                {midPoint && (
                  <Marker 
                    key={index} 
                    coordinate={midPoint}
                    pinColor={isSelected ? 'red' : 'blue'}
                  >
                    <Callout>
                      <View style={styles.calloutContainer}>
                        <Text style={styles.calloutTitle}>Curva {curve.classification}</Text>
                        <Text style={styles.calloutText}>Radio: {Math.round(curve.radius)}m</Text>
                        <Text style={styles.calloutText}>Giro: {Math.round(Math.abs(curve.heading_change))}°</Text>
                        <TouchableOpacity 
                          style={{marginTop: 5, backgroundColor: '#4285F4', padding: 5, borderRadius: 5, alignItems: 'center'}}
                          onPress={() => {
                            // Using a search query instead of forced pano avoids the black screen
                            // when Google has no Street View coverage in the mountains.
                            const url = `https://www.google.com/maps/search/?api=1&query=${midPoint.latitude},${midPoint.longitude}`;
                            if (Platform.OS === 'web') {
                              window.open(url, '_blank');
                            } else {
                              Linking.openURL(url);
                            }
                          }}
                        >
                          <Text style={{color: '#fff', fontSize: 12, fontWeight: 'bold'}}>Abrir en Maps</Text>
                        </TouchableOpacity>
                      </View>
                    </Callout>
                  </Marker>
                )}
              </React.Fragment>
            );
          })}

          {routeData && routeData.points && routeData.points.length > 0 && (
            <>
              <Marker coordinate={routeData.points[0]} title="Salida">
                 <FontAwesome5 name="flag-checkered" size={24} color="#00ff00" />
              </Marker>
              <Marker coordinate={routeData.points[routeData.points.length - 1]} title="Llegada">
                 <FontAwesome5 name="flag-checkered" size={24} color="#ff0000" />
              </Marker>
            </>
          )}
        </MapView>
      </View>

      <View style={styles.topOverlay}>
        <BlurView intensity={80} tint="dark" style={styles.blurHeader}>
          <Image source={require('../../assets/logoRecce.png')} style={styles.logo} resizeMode="contain" />
          
          <View style={styles.searchBox}>
             <FontAwesome5 name="map-marker-alt" size={16} color="#aaa" style={styles.inputIcon} />
             <TextInput
               style={styles.input}
               placeholder="Origen (Ej: Madrid)"
               placeholderTextColor="#888"
               value={origin}
               onChangeText={setOrigin}
             />
          </View>
          
          <View style={styles.searchBox}>
             <FontAwesome5 name="flag-checkered" size={16} color="#aaa" style={styles.inputIcon} />
             <TextInput
               style={styles.input}
               placeholder="Destino (Ej: Toledo)"
               placeholderTextColor="#888"
               value={destination}
               onChangeText={setDestination}
             />
          </View>

          <TouchableOpacity 
            style={[styles.generateBtn, loading && styles.generateBtnDisabled]} 
            onPress={handleGenerate} 
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.generateBtnText}>GENERAR RUTA</Text>
            )}
          </TouchableOpacity>
          
          <View style={styles.iconActionRow}>
             <TouchableOpacity style={[styles.iconBtn, isRecceMode && styles.iconBtnActive]} onPress={toggleRecceMode}>
               <FontAwesome5 name="map-marker-alt" size={16} color={isRecceMode ? "#fff" : "#ff4444"} />
               <Text style={styles.iconBtnText}>Recce</Text>
             </TouchableOpacity>
             <TouchableOpacity style={styles.iconBtn} onPress={handleUploadGPX}>
               <FontAwesome5 name="file-upload" size={16} color="#00C851" />
               <Text style={styles.iconBtnText}>GPX</Text>
             </TouchableOpacity>
             <TouchableOpacity style={styles.iconBtn} onPress={handleUploadTelemetry}>
               <FontAwesome5 name="car" size={16} color="#AA66CC" />
               <Text style={styles.iconBtnText}>CSV</Text>
             </TouchableOpacity>
          </View>
        </BlurView>
      </View>

      {routeData && !loading && (
        <View style={styles.listContainer}>
           <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.listHeaderScroll} contentContainerStyle={styles.listHeader}>
             <TouchableOpacity 
                style={[styles.settingsBtn, isRecording && {backgroundColor: '#ff4444'}]} 
                onPress={isRecording ? stopRecording : startRecording}
             >
               <FontAwesome5 name="microphone" size={14} color="#fff" />
               <Text style={styles.exportBtnText}>{isRecording ? "Grabando..." : "Voz"}</Text>
             </TouchableOpacity>
             <TouchableOpacity style={styles.settingsBtn} onPress={() => setShowSettings(true)}>
               <FontAwesome5 name="cogs" size={14} color="#fff" />
               <Text style={styles.exportBtnText}>Perfil</Text>
             </TouchableOpacity>
             <TouchableOpacity 
              style={[styles.settingsBtn, { backgroundColor: '#d60000' }]} 
              onPress={() => setShowExportModal(true)}
            >
              <FontAwesome5 name="file-pdf" size={14} color="#fff" />
              <Text style={styles.exportBtnText}>Exportar PDF</Text>
            </TouchableOpacity>
            {isPlaying ? (
              <TouchableOpacity 
                style={[styles.settingsBtn, { backgroundColor: '#555' }]} 
                onPress={handleStopSimulation}
              >
                <FontAwesome5 name="stop" size={14} color="#fff" />
                <Text style={styles.exportBtnText}>Stop</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity 
                style={[styles.settingsBtn, { backgroundColor: '#4285F4' }]} 
                onPress={handlePlaySimulation}
              >
                <FontAwesome5 name="play" size={14} color="#fff" />
                <Text style={styles.exportBtnText}>Simular</Text>
              </TouchableOpacity>
            )}
             <TouchableOpacity style={styles.settingsBtn} onPress={() => setShowTelemetry(true)}>
               <FontAwesome5 name="chart-line" size={14} color="#fff" />
               <Text style={styles.exportBtnText}>Telem.</Text>
             </TouchableOpacity>
             <TouchableOpacity style={styles.settingsBtn} onPress={handleExport}>
               <FontAwesome5 name="file-export" size={14} color="#fff" />
               <Text style={styles.exportBtnText}>CSV</Text>
             </TouchableOpacity>
           </ScrollView>
           <PacenoteList 
             notes={routeData.pacenotes} 
             onNotePress={handleNotePress} 
             selectedCurveIndex={selectedCurveIndex}
             onNoteEdit={handleNoteEdit}
           />
        </View>
      )}

      <Modal visible={showSettings} animationType="fade" transparent={true}>
        <BlurView intensity={90} tint="dark" style={styles.modalOverlay}>
          <View style={styles.modalContentGlass}>
            <Text style={{color: '#fff', fontSize: 22, fontFamily: 'Inter_700Bold', marginBottom: 20, textAlign: 'center'}}>Perfil del Piloto</Text>
            
            <View style={styles.settingRow}>
              <Text style={styles.settingLabel}>Nombre / ID Piloto:</Text>
              <TextInput 
                style={[styles.settingInput, { flex: 1, minWidth: 150 }]}
                value={driverId}
                onChangeText={setDriverId}
              />
            </View>

            <Text style={{color: '#aaa', fontSize: 14, fontFamily: 'Inter_700Bold', marginTop: 15, marginBottom: 15}}>Umbrales de Curvas (metros)</Text>
            {Object.keys(thresholds).sort((a,b) => parseInt(b) - parseInt(a)).map((level) => (
              <View key={level} style={styles.settingRow}>
                <Text style={styles.settingLabel}>Curva {level}</Text>
                <TextInput 
                  style={styles.settingInput}
                  keyboardType="numeric"
                  value={thresholds[level as keyof typeof thresholds]}
                  onChangeText={(val) => setThresholds({...thresholds, [level]: val})}
                />
              </View>
            ))}

            <TouchableOpacity style={[styles.generateBtn, {marginTop: 20}]} onPress={() => setShowSettings(false)}>
              <Text style={styles.generateBtnText}>GUARDAR</Text>
            </TouchableOpacity>
          </View>
        </BlurView>
      </Modal>

      <Modal visible={streetViewCoord !== null} animationType="slide">
        <View style={{flex: 1, backgroundColor: '#000'}}>
          <View style={styles.streetViewHeader}>
            <TouchableOpacity onPress={() => setStreetViewCoord(null)} style={styles.closeBtn}>
              <FontAwesome5 name="arrow-left" size={20} color="#fff" />
              <Text style={{color: '#fff', marginLeft: 10, fontFamily: 'Inter_700Bold'}}>Volver al Mapa</Text>
            </TouchableOpacity>
          </View>
          {streetViewCoord && (
            <WebView 
              source={{ uri: `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${streetViewCoord.lat},${streetViewCoord.lng}` }}
              style={{flex: 1}}
            />
          )}
        </View>
      </Modal>

      {/* Telemetry Modal */}
      <Modal visible={showTelemetry} animationType="slide" transparent={true}>
        <BlurView intensity={95} tint="dark" style={{flex: 1}}>
          <View style={styles.streetViewHeader}>
            <TouchableOpacity onPress={() => setShowTelemetry(false)} style={styles.closeBtn}>
              <FontAwesome5 name="arrow-left" size={20} color="#fff" />
              <Text style={{color: '#fff', marginLeft: 10, fontFamily: 'Inter_700Bold'}}>Cerrar Telemetría</Text>
            </TouchableOpacity>
          </View>
          {showTelemetry && routeData && routeData.speed_profile && (
            <View style={{flex: 1, padding: 20}}>
               <Text style={{color: '#fff', fontSize: 24, fontWeight: 'bold', marginBottom: 20, textAlign: 'center'}}>Perfil de Velocidad Teórica</Text>
               <ScrollView horizontal style={{flex: 1, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 10, padding: 20}} contentContainerStyle={{alignItems: 'flex-end', paddingBottom: 20}}>
                 {routeData.speed_profile.map((v: number, i: number) => {
                    const height = (v / 40) * 300; // max speed 40m/s
                    return (
                      <View key={i} style={{
                        width: 4,
                        height: height,
                        backgroundColor: '#00C851',
                        marginRight: 2,
                        borderTopLeftRadius: 2,
                        borderTopRightRadius: 2,
                        opacity: 0.8
                      }} />
                    )
                 })}
               </ScrollView>
               <Text style={{color: '#aaa', textAlign: 'center', marginTop: 10}}>Distancia →</Text>
            </View>
          )}
        </BlurView>
      </Modal>

      {/* Export Snapshot Modal */}
      <Modal visible={showExportModal} animationType="slide" transparent={true}>
        <BlurView intensity={95} tint="dark" style={{flex: 1}}>
          <View style={[styles.streetViewHeader, {backgroundColor: 'transparent'}]}>
            <TouchableOpacity onPress={() => setShowExportModal(false)} style={styles.closeBtn}>
              <FontAwesome5 name="arrow-left" size={20} color="#fff" />
              <Text style={{color: '#fff', marginLeft: 10, fontFamily: 'Inter_700Bold'}}>Volver</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={captureAndShare} style={[styles.closeBtn, {backgroundColor: '#d60000', paddingHorizontal: 15, borderRadius: 5, marginRight: 10}]}>
              <FontAwesome5 name="file-pdf" size={16} color="#fff" />
              <Text style={{color: '#fff', marginLeft: 10, fontFamily: 'Inter_700Bold'}}>PDF</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={exportSimulatorCSV} style={[styles.closeBtn, {backgroundColor: '#4285F4', paddingHorizontal: 15, borderRadius: 5}]}>
              <FontAwesome5 name="gamepad" size={16} color="#fff" />
              <Text style={{color: '#fff', marginLeft: 10, fontFamily: 'Inter_700Bold'}}>Simulador (CSV)</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={{flex: 1, backgroundColor: '#ececec'}} contentContainerStyle={{padding: 20}}>
            <ViewShot ref={viewShotRef} options={{ format: "png", quality: 0.9 }}>
              <View style={{backgroundColor: '#fff', padding: 20, borderRadius: 10}}>
                <Text style={{fontSize: 24, fontWeight: 'bold', textAlign: 'center', color: '#d60000', marginBottom: 10}}>NOTAS DE RALLY</Text>
                <Text style={{fontSize: 16, textAlign: 'center', marginBottom: 20}}>Piloto: {driverId}</Text>
                
                {routeData && routeData.pacenotes && routeData.pacenotes.map((note: any, index: number) => {
                  if (note.type === 'distance') {
                    return (
                      <View key={index} style={{backgroundColor: '#f0f0f0', padding: 10, borderBottomWidth: 1, borderColor: '#ccc'}}>
                        <Text style={{textAlign: 'center', color: '#555', fontSize: 18, fontWeight: 'bold'}}>{note.text} m</Text>
                      </View>
                    );
                  }
                  
                  const isRight = note.text.toLowerCase().includes('derecha');
                  const isLeft = note.text.toLowerCase().includes('izquierda');
                  const arrow = isRight ? '➔' : (isLeft ? '➔' : '↑');
                  const isCrest = note.text.toLowerCase().includes('rasante') || note.text.toLowerCase().includes('salto');
                  const icon = isCrest ? '⛰️' : arrow;

                  return (
                    <View key={index} style={{flexDirection: 'row', padding: 15, borderBottomWidth: 1, borderColor: '#eee', alignItems: 'center'}}>
                      <Text style={{fontSize: 24, color: '#d60000', width: 50, textAlign: 'center', transform: isLeft ? [{rotate: '180deg'}] : []}}>{icon}</Text>
                      <Text style={{fontSize: 20, fontWeight: 'bold', flex: 1, textTransform: 'uppercase'}}>{note.text}</Text>
                    </View>
                  );
                })}
              </View>
            </ViewShot>
          </ScrollView>
        </BlurView>
      </Modal>

    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  mapContainer: {
    ...StyleSheet.absoluteFillObject,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  topOverlay: {
    position: 'absolute',
    top: 40,
    left: 20,
    right: 20,
    zIndex: 10,
  },
  blurHeader: {
    borderRadius: 24,
    padding: 20,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    backgroundColor: 'rgba(20,20,20,0.5)',
  },
  logo: {
    height: 40,
    width: '100%',
    marginBottom: 20,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 10,
    marginBottom: 10,
    paddingHorizontal: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    height: 45,
    color: '#fff',
    fontFamily: 'Inter_400Regular',
  },
  generateBtn: {
    backgroundColor: '#d60000',
    borderRadius: 12,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
    shadowColor: '#d60000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.6,
    shadowRadius: 15,
    elevation: 8,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 5,
  },
  generateBtnDisabled: {
    backgroundColor: '#555',
    shadowOpacity: 0,
  },
  generateBtnText: {
    color: '#fff',
    fontFamily: 'Inter_700Bold',
    fontSize: 16,
    letterSpacing: 1.5,
  },
  iconActionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 15,
  },
  iconBtn: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 5,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  iconBtnActive: {
    backgroundColor: '#ff4444',
    borderColor: '#ff4444',
  },
  iconBtnText: {
    color: '#fff',
    fontFamily: 'Inter_400Regular',
    fontSize: 12,
    marginTop: 5,
  },
  listContainer: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    height: height * 0.40,
    zIndex: 10,
  },
  listHeaderScroll: {
    maxHeight: 40,
    marginBottom: 10,
  },
  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingRight: 20,
  },
  exportBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 153, 255, 0.8)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  settingsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginRight: 10,
  },
  exportBtnText: {
    color: '#fff',
    fontFamily: 'Inter_700Bold',
    marginLeft: 5,
    fontSize: 12,
  },
  calloutContainer: {
    padding: 5,
    width: 150,
  },
  calloutTitle: {
    fontWeight: 'bold',
    fontSize: 14,
    marginBottom: 2,
  },
  calloutText: {
    fontSize: 12,
    color: '#666',
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContentGlass: {
    width: '100%',
    padding: 25,
    borderRadius: 24,
    backgroundColor: 'rgba(30,30,30,0.6)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  settingLabel: {
    color: '#fff',
    fontFamily: 'Inter_400Regular',
  },
  settingInput: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    color: '#fff',
    padding: 5,
    borderRadius: 5,
    width: 60,
    textAlign: 'center',
    fontFamily: 'Inter_700Bold',
  },
  streetViewHeader: {
    height: 60,
    backgroundColor: 'transparent',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    marginTop: Platform.OS === 'ios' ? 40 : 20,
  },
  closeBtn: {
    flexDirection: 'row',
    alignItems: 'center',
  }
});

export default MapScreen;
