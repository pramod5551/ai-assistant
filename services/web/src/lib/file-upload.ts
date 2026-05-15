/** Client-side helpers for ingest file picks (text + binary). */

const TEXT_EXT = /\.(txt|md|markdown|csv|json)$/i;

export function isTextFileName(name: string): boolean {
  return TEXT_EXT.test(name);
}

/** Base64-encode an ArrayBuffer without blowing the call stack on large files. */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export type FileUploadPayload = {
  file_name: string;
  content?: string;
  content_base64?: string;
};

export async function fileToUploadPayload(
  file: File,
  maxBytes: number,
): Promise<FileUploadPayload> {
  if (file.size > maxBytes) {
    throw new Error(
      `${file.name} is too large (${formatBytes(file.size)}; max ${formatBytes(maxBytes)})`,
    );
  }

  if (isTextFileName(file.name)) {
    const content = await file.text();
    if (!content.trim()) {
      throw new Error(`${file.name} is empty`);
    }
    return { file_name: file.name, content };
  }

  const buffer = await file.arrayBuffer();
  return {
    file_name: file.name,
    content_base64: arrayBufferToBase64(buffer),
  };
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** Slug from filename for document_id (no extension). */
export function slugFromFileName(name: string): string {
  const base = name.replace(/\.[^.]+$/, "").toLowerCase();
  const slug = base.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug.slice(0, 64) || `doc-${Date.now()}`;
}

/** Pick a document_id that is not already in `used`. */
export function uniqueDocumentId(base: string, used: Set<string>): string {
  const root = base.slice(0, 64) || "doc";
  let candidate = root;
  let n = 2;
  while (used.has(candidate)) {
    const suffix = `-${n}`;
    candidate = `${root.slice(0, Math.max(1, 64 - suffix.length))}${suffix}`;
    n += 1;
  }
  used.add(candidate);
  return candidate;
}

export type ParsedUploadFile = {
  fileName: string;
  document_id: string;
  title: string;
  content?: string;
  content_base64?: string;
};

/** Parse many files for one ingest request; skips failures and returns per-file errors. */
export async function filesToUploadPayloads(
  files: File[],
  maxBytes: number,
  usedDocumentIds: Set<string>,
): Promise<{ uploads: ParsedUploadFile[]; errors: string[] }> {
  const uploads: ParsedUploadFile[] = [];
  const errors: string[] = [];
  for (const file of files) {
    try {
      const payload = await fileToUploadPayload(file, maxBytes);
      const base = slugFromFileName(file.name);
      const document_id = uniqueDocumentId(base, usedDocumentIds);
      uploads.push({
        fileName: file.name,
        document_id,
        title: file.name.replace(/\.[^.]+$/, ""),
        content: payload.content,
        content_base64: payload.content_base64,
      });
    } catch (e) {
      errors.push(e instanceof Error ? e.message : `Failed: ${file.name}`);
    }
  }
  return { uploads, errors };
}
