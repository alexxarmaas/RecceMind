import axios from 'axios';
import { Platform } from 'react-native';

import type {
  FeedbackResponse,
  RouteAnalysisResponse,
  SpeechResponse,
  Thresholds,
} from '../types/api';

const developmentHost = Platform.select({
  android: 'http://10.0.2.2:8000',
  default: 'http://127.0.0.1:8000',
});

const configuredBaseUrl = process.env.EXPO_PUBLIC_API_URL?.trim() || developmentHost;
const normalizedBaseUrl = configuredBaseUrl.replace(/\/$/, '');
const apiBaseUrl = normalizedBaseUrl.endsWith('/api')
  ? normalizedBaseUrl
  : `${normalizedBaseUrl}/api`;

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
});

interface DriverOptions {
  thresholds?: Partial<Thresholds>;
  driverId?: string;
}

const driverPayload = ({ thresholds, driverId }: DriverOptions) => ({
  ...(thresholds ? { thresholds } : {}),
  ...(driverId ? { driver_id: driverId } : {}),
});

export const analyzeRoute = async (
  origin: string,
  destination: string,
  thresholds?: Partial<Thresholds>,
  driverId?: string,
): Promise<RouteAnalysisResponse> => {
  const response = await api.post<RouteAnalysisResponse>('/analyze-route', {
    origin,
    destination,
    ...driverPayload({ thresholds, driverId }),
  });
  return response.data;
};

export const processGpx = async (
  gpxContent: string,
  thresholds?: Partial<Thresholds>,
  driverId?: string,
): Promise<RouteAnalysisResponse> => {
  const response = await api.post<RouteAnalysisResponse>('/process-gpx', {
    gpx_content: gpxContent,
    ...driverPayload({ thresholds, driverId }),
  });
  return response.data;
};

export const processPolyline = async (
  encodedPolyline: string,
  thresholds?: Partial<Thresholds>,
  driverId?: string,
): Promise<RouteAnalysisResponse> => {
  const response = await api.post<RouteAnalysisResponse>('/process-polyline', {
    polyline: encodedPolyline,
    ...driverPayload({ thresholds, driverId }),
  });
  return response.data;
};

export const processCoords = async (
  coordinates: number[][],
  thresholds?: Partial<Thresholds>,
  driverId?: string,
): Promise<RouteAnalysisResponse> => {
  const response = await api.post<RouteAnalysisResponse>('/process-coords', {
    coordinates,
    ...driverPayload({ thresholds, driverId }),
  });
  return response.data;
};

export const submitFeedback = async (
  radius: number,
  headingChange: number,
  length: number,
  originalClassification: number,
  userClassification: number,
  driverId = 'default',
): Promise<FeedbackResponse> => {
  const response = await api.post<FeedbackResponse>('/feedback', {
    radius,
    heading_change: headingChange,
    length,
    original_classification: originalClassification,
    user_classification: userClassification,
    driver_id: driverId,
  });
  return response.data;
};

export const transcribeAudio = async (uri: string): Promise<SpeechResponse> => {
  const formData = new FormData();
  const filename = uri.split('/').pop() || 'audio.m4a';
  const extension = /\.(\w+)$/.exec(filename)?.[1];
  const mimeType = extension ? `audio/${extension}` : 'audio/m4a';

  formData.append('audio', { uri, name: filename, type: mimeType } as unknown as Blob);
  const response = await api.post<SpeechResponse>('/speech-to-text', formData);
  return response.data;
};

export const processTelemetry = async (
  file: File | Blob,
  thresholds?: Partial<Thresholds>,
  driverId?: string,
): Promise<RouteAnalysisResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  if (thresholds) formData.append('thresholds', JSON.stringify(thresholds));
  if (driverId) formData.append('driver_id', driverId);

  const response = await api.post<RouteAnalysisResponse>('/process-telemetry', formData);
  return response.data;
};

export { apiBaseUrl };
