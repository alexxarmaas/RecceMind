import type { Component, ReactNode, RefObject } from 'react';
import type { ViewProps } from 'react-native';

export interface CaptureOptions {
  width?: number;
  height?: number;
  format?: 'png' | 'jpg' | 'webm' | 'raw';
  quality?: number;
  result?: 'tmpfile' | 'base64' | 'data-uri' | 'zip-base64';
  fileName?: string;
  snapshotContentContainer?: boolean;
  useRenderInContext?: boolean;
  handleGLSurfaceViewOnAndroid?: boolean;
}

export interface ViewShotProps extends ViewProps {
  children?: ReactNode;
  options?: CaptureOptions;
  captureMode?: 'mount' | 'continuous' | 'update';
  onCapture?: (uri: string) => void;
  onCaptureFailure?: (error: Error) => void;
}

export default class ViewShot extends Component<ViewShotProps> {
  capture(): Promise<string>;
}

export function captureRef(
  view: number | RefObject<unknown> | Component,
  options?: CaptureOptions,
): Promise<string>;

export function captureScreen(options?: CaptureOptions): Promise<string>;
export function releaseCapture(uri: string): void;
