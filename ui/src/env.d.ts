interface ImportMetaEnv {
  readonly VITE_DEFAULT_API_BASE?: string;
  readonly VITE_DEFAULT_SCAN_TIMEOUT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
