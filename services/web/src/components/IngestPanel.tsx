"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";

import type {
  IngestCatalogResponse,
  IngestRequest,
  IngestResponse,
  PendingUpload,
} from "@/lib/ingest-types";
import { formatUserFacingError } from "@/lib/api-errors";
import { filesToUploadPayloads } from "@/lib/file-upload";

import styles from "./IngestPanel.module.css";

const DEFAULT_ACCEPT =
  ".txt,.md,.markdown,.pdf,.doc,.docx,.rtf,.html,.htm,.csv,.json,.pptx";
const DEFAULT_MAX_BYTES = 10_485_760;

const DEFAULT_OPTIONS: IngestRequest["options"] = {
  batch_size: 32,
  max_chars: 1100,
  overlap: 120,
  recreate_collection: false,
  dry_run: false,
};

function usedDocumentIds(uploads: PendingUpload[]): Set<string> {
  return new Set(uploads.map((u) => u.document_id));
}

export function IngestPanel() {
  const fileInputId = useId();
  const fileRef = useRef<HTMLInputElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  const [catalog, setCatalog] = useState<IngestCatalogResponse | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);

  const [uploads, setUploads] = useState<PendingUpload[]>([]);
  const [defaultLibrary, setDefaultLibrary] = useState("POLICIES");
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [dragActive, setDragActive] = useState(false);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  const libraries =
    catalog?.libraries?.length
      ? catalog.libraries
      : ["POLICIES", "PROCEDURES", "EXTERNAL_REF"];

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingCatalog(true);
      setCatalogError(null);
      try {
        const res = await fetch("/api/ingest/catalog");
        const data = await res.json();
        if (!res.ok) {
          throw new Error(formatUserFacingError(res.status, data));
        }
        if (!cancelled) {
          setCatalog(data as IngestCatalogResponse);
          if (data.libraries?.[0]) setDefaultLibrary(data.libraries[0]);
        }
      } catch (e) {
        if (!cancelled) {
          setCatalogError(
            e instanceof Error ? e.message : "Failed to load ingest settings",
          );
        }
      } finally {
        if (!cancelled) setLoadingCatalog(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const maxUploadBytes = catalog?.max_upload_bytes ?? DEFAULT_MAX_BYTES;
  const acceptTypes = catalog?.accept_file_types ?? DEFAULT_ACCEPT;

  const addFiles = async (files: FileList | File[] | null) => {
    if (!files?.length) return;
    const list = Array.from(files);
    const used = usedDocumentIds(uploads);
    const { uploads: parsed, errors } = await filesToUploadPayloads(
      list,
      maxUploadBytes,
      used,
    );
    if (parsed.length) {
      setUploads((prev) => [
        ...prev,
        ...parsed.map((p) => ({
          id: crypto.randomUUID(),
          fileName: p.fileName,
          document_id: p.document_id,
          title: p.title,
          library_id: defaultLibrary,
          content: p.content,
          content_base64: p.content_base64,
        })),
      ]);
    }
    if (errors.length) setError(errors.join(" · "));
    else if (parsed.length) setError(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const onFilesChosen = (files: FileList | null) => {
    void addFiles(files);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (running) return;
    void addFiles(e.dataTransfer.files);
  };

  const removeUpload = (id: string) => {
    setUploads((u) => u.filter((x) => x.id !== id));
  };

  const clearUploads = () => setUploads([]);

  const updateUpload = (id: string, patch: Partial<PendingUpload>) => {
    setUploads((u) => u.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  };

  const applyLibraryToAllUploads = () => {
    setUploads((u) => u.map((x) => ({ ...x, library_id: defaultLibrary })));
  };

  const buildRequest = useCallback(
    (dryRun: boolean): IngestRequest => ({
      uploads: uploads.map((u) => ({
        document_id: u.document_id,
        title: u.title,
        library_id: u.library_id,
        file_name: u.fileName,
        ...(u.content_base64
          ? { content_base64: u.content_base64 }
          : { content: u.content ?? "" }),
      })),
      options: { ...options, dry_run: dryRun },
    }),
    [uploads, options],
  );

  const runIngest = async (dryRun: boolean) => {
    if (uploads.length === 0) {
      setError("Add at least one file to upload.");
      return;
    }
    if (options.recreate_collection && !dryRun) {
      const ok = window.confirm(
        "This will delete the entire vector collection and re-ingest. Continue?",
      );
      if (!ok) return;
    }

    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/ingest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRequest(dryRun)),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          typeof data?.message === "string"
            ? data.message
            : formatUserFacingError(res.status, data),
        );
      }
      const ingested = data as IngestResponse;
      setResult(ingested);
      if (ingested.documents.length < uploads.length) {
        setError(
          `Only ${ingested.documents.length} of ${uploads.length} file(s) were indexed. Check the result list below.`,
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setRunning(false);
    }
  };

  if (loadingCatalog) {
    return <p className={styles.loading}>Loading ingest settings…</p>;
  }

  return (
    <div className={styles.panel}>
      <div className={styles.scroll}>
        <p className={styles.intro}>
          Upload your documents here. Text is extracted on the server, chunked, and
          stored in Qdrant so the chat can search them
          {catalog ? (
            <span className={styles.badge}>{catalog.collection}</span>
          ) : null}
          . Ingest at least one file before asking questions on the Chat tab.
        </p>
        {catalog?.supported_formats && catalog.supported_formats.length > 0 && (
          <p className={styles.formatList}>
            Supported: {catalog.supported_formats.join(" · ")}
          </p>
        )}

        {catalogError && (
          <p className={`${styles.alert} ${styles.alertError}`} role="alert">
            {catalogError}
          </p>
        )}

        <section className={styles.section} aria-labelledby="ingest-options">
          <h2 id="ingest-options" className={styles.sectionTitle}>
            Options
          </h2>
          <div className={styles.card}>
            <div className={styles.optionsGrid}>
              <div className={styles.field}>
                <label htmlFor="batch-size">Batch size</label>
                <input
                  id="batch-size"
                  type="number"
                  min={1}
                  max={256}
                  value={options.batch_size}
                  disabled={running}
                  onChange={(e) =>
                    setOptions((o) => ({
                      ...o,
                      batch_size: Number(e.target.value) || 32,
                    }))
                  }
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="max-chars">Chunk size (chars)</label>
                <input
                  id="max-chars"
                  type="number"
                  min={200}
                  max={8000}
                  value={options.max_chars}
                  disabled={running}
                  onChange={(e) =>
                    setOptions((o) => ({
                      ...o,
                      max_chars: Number(e.target.value) || 1100,
                    }))
                  }
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="overlap">Overlap (chars)</label>
                <input
                  id="overlap"
                  type="number"
                  min={0}
                  max={2000}
                  value={options.overlap}
                  disabled={running}
                  onChange={(e) =>
                    setOptions((o) => ({
                      ...o,
                      overlap: Number(e.target.value) || 0,
                    }))
                  }
                />
              </div>
              <div className={`${styles.checkboxRow} ${styles.fieldFull}`}>
                <label>
                  <input
                    type="checkbox"
                    checked={options.recreate_collection}
                    disabled={running}
                    onChange={(e) =>
                      setOptions((o) => ({
                        ...o,
                        recreate_collection: e.target.checked,
                      }))
                    }
                  />
                  Recreate collection (destructive — wipes all indexed documents)
                </label>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="upload-docs">
          <h2 id="upload-docs" className={styles.sectionTitle}>
            Your documents
          </h2>
          <p className={styles.sectionHint}>
            Add one or more files (drag and drop or file picker). Max{" "}
            {Math.round(maxUploadBytes / (1024 * 1024))} MB per file. All queued files
            are indexed in a single run.
          </p>

          <div className={styles.batchRow}>
            <div className={styles.field}>
              <label htmlFor="default-library">Default library for new files</label>
              <select
                id="default-library"
                value={defaultLibrary}
                disabled={running}
                onChange={(e) => setDefaultLibrary(e.target.value)}
              >
                {libraries.map((lib) => (
                  <option key={lib} value={lib}>
                    {lib}
                  </option>
                ))}
              </select>
            </div>
            {uploads.length > 1 && (
              <button
                type="button"
                className={styles.linkBtn}
                disabled={running}
                onClick={applyLibraryToAllUploads}
              >
                Apply library to all
              </button>
            )}
          </div>

          <div
            ref={dropRef}
            className={`${styles.dropZone} ${dragActive ? styles.dropZoneActive : ""}`}
            onDragEnter={(e) => {
              e.preventDefault();
              if (!running) setDragActive(true);
            }}
            onDragLeave={(e) => {
              if (e.currentTarget === dropRef.current) setDragActive(false);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
          >
            <input
              ref={fileRef}
              id={fileInputId}
              className={styles.fileInput}
              type="file"
              accept={acceptTypes}
              multiple
              disabled={running}
              onChange={(e) => onFilesChosen(e.target.files)}
            />
            <p className={styles.dropTitle}>Drop files here</p>
            <p className={styles.dropSub}>or</p>
            <label htmlFor={fileInputId} className={styles.uploadBtn}>
              Choose files…
            </label>
          </div>

          {uploads.length > 0 && (
            <>
              <div className={styles.toolbar}>
                <span className={styles.countBadge}>
                  {uploads.length} file{uploads.length === 1 ? "" : "s"} queued
                </span>
                <button
                  type="button"
                  className={styles.linkBtn}
                  disabled={running}
                  onClick={() => fileRef.current?.click()}
                >
                  Add more…
                </button>
                <button
                  type="button"
                  className={styles.linkBtn}
                  disabled={running}
                  onClick={clearUploads}
                >
                  Clear all
                </button>
              </div>
              <div className={styles.uploadList}>
                {uploads.map((u) => (
                  <div key={u.id} className={styles.uploadCard}>
                    <div className={styles.uploadCardHeader}>
                      <span className={styles.uploadFileName}>{u.fileName}</span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        disabled={running}
                        onClick={() => removeUpload(u.id)}
                      >
                        Remove
                      </button>
                    </div>
                    <div className={styles.uploadFields}>
                      <div className={`${styles.field} ${styles.fieldFull}`}>
                        <label>Title</label>
                        <input
                          value={u.title}
                          disabled={running}
                          onChange={(e) =>
                            updateUpload(u.id, { title: e.target.value })
                          }
                        />
                      </div>
                      <div className={styles.field}>
                        <label>Document ID</label>
                        <input
                          value={u.document_id}
                          disabled={running}
                          onChange={(e) =>
                            updateUpload(u.id, { document_id: e.target.value })
                          }
                        />
                      </div>
                      <div className={styles.field}>
                        <label>Library</label>
                        <select
                          value={u.library_id}
                          disabled={running}
                          onChange={(e) =>
                            updateUpload(u.id, { library_id: e.target.value })
                          }
                        >
                          {libraries.map((lib) => (
                            <option key={lib} value={lib}>
                              {lib}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        {result && (
          <section className={styles.section} aria-live="polite">
            <div className={`${styles.alert} ${styles.alertSuccess}`}>
              {result.dry_run ? "Preview" : "Ingest complete"}:{" "}
              {result.documents.length} document
              {result.documents.length === 1 ? "" : "s"}, {result.chunks_total}{" "}
              chunk(s)
              {result.dry_run
                ? " (dry run — nothing written)"
                : `, ${result.points_upserted} point(s) upserted`}
              {result.recreated_collection ? " · collection recreated" : ""}.
            </div>
            <ul className={styles.resultList}>
              {result.documents.map((d) => (
                <li key={d.document_id}>
                  <strong>{d.title}</strong> ({d.document_id}) — {d.chunk_count}{" "}
                  chunk(s), {d.library_id}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <footer className={styles.footer}>
        {error && (
          <p className={`${styles.alert} ${styles.alertError}`} role="alert">
            {error}
          </p>
        )}
        <p className={styles.selectionSummary}>
          Ready to index <strong>{uploads.length}</strong> document
          {uploads.length === 1 ? "" : "s"}.
        </p>
        <div className={styles.footerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            disabled={running || uploads.length === 0}
            onClick={() => void runIngest(true)}
          >
            Preview chunks
          </button>
          <button
            type="button"
            className={styles.btnPrimary}
            disabled={running || uploads.length === 0}
            onClick={() => void runIngest(false)}
          >
            {running
              ? "Indexing…"
              : `Run ingestion (${uploads.length} file${uploads.length === 1 ? "" : "s"})`}
          </button>
        </div>
      </footer>
    </div>
  );
}
