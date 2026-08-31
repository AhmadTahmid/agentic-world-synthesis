/// <reference types="vite/client" />

interface Window {
  __WORLD_READY__?: boolean;
  __WORLD_DEBUG__?: {
    applyCapturePreset(name: string): void;
    getMetrics(): Record<string, unknown>;
    getScatterManifest(): unknown;
    getAssetStats(): Promise<Record<string, unknown>>;
    setInspectorVisible(visible: boolean): void;
  };
}
