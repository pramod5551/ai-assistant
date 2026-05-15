export type IngestCatalogResponse = {
  libraries: string[];
  collection: string;
  vector_backend: string;
  supported_extensions?: string[];
  supported_formats?: string[];
  accept_file_types?: string;
  max_upload_bytes?: number;
};

export type UploadDocument = {
  document_id: string;
  title: string;
  library_id: string;
  file_name?: string;
  content?: string;
  content_base64?: string;
};

export type IngestOptions = {
  batch_size: number;
  max_chars: number;
  overlap: number;
  recreate_collection: boolean;
  dry_run: boolean;
};

export type IngestRequest = {
  uploads: UploadDocument[];
  options: IngestOptions;
};

export type IngestDocumentSummary = {
  document_id: string;
  title: string;
  library_id: string;
  chunk_count: number;
  source: string;
};

export type IngestResponse = {
  collection: string;
  chunks_total: number;
  points_upserted: number;
  documents: IngestDocumentSummary[];
  dry_run: boolean;
  recreated_collection: boolean;
};

export type PendingUpload = {
  id: string;
  fileName: string;
  document_id: string;
  title: string;
  library_id: string;
  content?: string;
  content_base64?: string;
};
