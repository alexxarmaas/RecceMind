import axios from 'axios';
import { Platform } from 'react-native';

// Para acceso remoto via túnel Cloudflare
const API_URL = 'https://telling-elect-hour-mice.trycloudflare.com/api';

export const analyzeRoute = async (origin: string, destination: string, thresholds?: any, driverId?: string) => {
  try {
    const payload: any = { origin, destination };
    if (thresholds) {
      payload.thresholds = thresholds;
    }
    if (driverId) {
      payload.driver_id = driverId;
    }
    const response = await axios.post(`${API_URL}/analyze-route`, payload);
    return response.data;
  } catch (error) {
    console.error('Error analyzing route:', error);
    throw error;
  }
};

export const processGpx = async (gpxContent: string, thresholds?: any, driverId?: string) => {
  try {
    const payload: any = { gpx_content: gpxContent };
    if (thresholds) {
      payload.thresholds = thresholds;
    }
    if (driverId) {
      payload.driver_id = driverId;
    }
    const response = await axios.post(`${API_URL}/process-gpx`, payload);
    return response.data;
  } catch (error) {
    console.error('Error processing GPX:', error);
    throw error;
  }
};

export const processPolyline = async (polyline: string, thresholds?: any, driverId?: string) => {
  try {
    const payload: any = { polyline };
    if (thresholds) {
      payload.thresholds = thresholds;
    }
    if (driverId) {
      payload.driver_id = driverId;
    }
    const response = await axios.post(`${API_URL}/process-polyline`, payload);
    return response.data;
  } catch (error) {
    console.error('Error processing polyline:', error);
    throw error;
  }
};

export const processCoords = async (coordinates: number[][], thresholds?: any, driverId?: string) => {
  try {
    const payload: any = { coordinates };
    if (thresholds) {
      payload.thresholds = thresholds;
    }
    if (driverId) {
      payload.driver_id = driverId;
    }
    const response = await axios.post(`${API_URL}/process-coords`, payload);
    return response.data;
  } catch (error) {
    console.error('Error processing coords:', error);
    throw error;
  }
};

export const submitFeedback = async (
  radius: number,
  headingChange: number,
  length: number,
  originalClassification: number,
  userClassification: number,
  driverId?: string
) => {
  try {
    const payload = {
      radius,
      heading_change: headingChange,
      length,
      original_classification: originalClassification,
      user_classification: userClassification,
      driver_id: driverId || 'default'
    };
    const response = await axios.post(`${API_URL}/feedback`, payload);
    return response.data;
  } catch (error) {
    console.error('Error submitting feedback:', error);
    throw error;
  }
};

export const transcribeAudio = async (uri: string) => {
  try {
    const formData = new FormData();
    const filename = uri.split('/').pop() || 'audio.m4a';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `audio/${match[1]}` : `audio`;
    
    // @ts-ignore
    formData.append('audio', { uri, name: filename, type });
    
    const response = await axios.post(`${API_URL}/speech-to-text`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    console.error('Error transcribing audio:', error);
    throw error;
  }
};

export const processTelemetry = async (file: File | any, thresholds?: any, driverId?: string) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    if (thresholds) {
      formData.append('thresholds', JSON.stringify(thresholds));
    }
    if (driverId) {
      formData.append('driver_id', driverId);
    }
    
    const response = await axios.post(`${API_URL}/process-telemetry`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    console.error('Error processing telemetry:', error);
    throw error;
  }
};
