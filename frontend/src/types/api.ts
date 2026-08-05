export interface PacenoteItem {
  type: 'distance' | 'note';
  text: string;
  curve_index: number | null;
  distance?: number;
}

export interface CurveData {
  start_idx: number;
  end_idx: number;
  start_distance: number;
  end_distance: number;
  length: number;
  radius: number;
  heading_change: number;
  direction: 'Derecha' | 'Izquierda';
  modifier: string;
  classification: number;
  max_speed?: number;
  min_gear?: number;
  max_braking?: number;
}

export interface RouteAnalysisResponse {
  polyline: string;
  distanceMeters?: number;
  duration?: string;
  curves: CurveData[];
  pacenotes: PacenoteItem[];
  speed_profile: number[];
}

export interface FeedbackResponse {
  message: string;
  ml_trained: boolean;
  total_feedbacks: number;
}

export interface SpeechResponse {
  text: string;
  error?: string;
}

export type Thresholds = Record<2 | 3 | 4 | 5 | 6, number>;
