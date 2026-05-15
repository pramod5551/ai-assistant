/** Map API / BFF error payloads to short, user-facing copy (no raw JSON). */

type JsonObject = Record<string, unknown>;

function isObject(v: unknown): v is JsonObject {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseJsonMaybe(value: unknown): unknown {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return value;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return value;
  }
}

function looksLikeTimeout(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("timed out") ||
    lower.includes("timeout") ||
    lower.includes("time out")
  );
}

function looksLikeUnreachable(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("cannot reach") ||
    lower.includes("connection refused") ||
    lower.includes("not reachable") ||
    lower.includes("could not reach")
  );
}

function defaultForStatus(status: number): string {
  if (status === 408 || status === 504) {
    return "The assistant took too long to respond. Try a shorter question, or wait a minute and try again (the model may still be loading).";
  }
  if (status === 503 || status === 502) {
    return "The assistant is temporarily unavailable. Check that the backend services are running, then try again.";
  }
  if (status === 401 || status === 403) {
    return "You are not signed in or do not have access to this assistant.";
  }
  if (status === 400) {
    return "That request could not be processed. Check your input and try again.";
  }
  if (status >= 500) {
    return "Something went wrong on the server. Please try again in a moment.";
  }
  return "Something went wrong. Please try again.";
}

function messageFromProblemDetail(pd: JsonObject, status: number): string | null {
  const detail = pd.detail;
  if (typeof detail === "string" && detail.trim()) {
    if (!detail.startsWith("{") && detail.length < 280) {
      return detail;
    }
  }
  const cause = pd.cause;
  if (typeof cause === "string" && looksLikeTimeout(cause)) {
    return defaultForStatus(504);
  }
  if (typeof cause === "string" && looksLikeUnreachable(cause)) {
    return defaultForStatus(503);
  }
  if (typeof detail === "string" && looksLikeTimeout(detail)) {
    return defaultForStatus(504);
  }
  if (typeof detail === "string" && looksLikeUnreachable(detail)) {
    return defaultForStatus(503);
  }
  return null;
}

/**
 * Turn a failed HTTP response body into copy suitable for the UI.
 */
export function formatUserFacingError(status: number, payload: unknown): string {
  let body = parseJsonMaybe(payload);

  if (isObject(body)) {
    // Next.js proxy: { error, detail, status }
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message.trim();
    }

    const nested = parseJsonMaybe(body.detail);
    if (nested !== body.detail) {
      const fromNested = formatUserFacingError(status, nested);
      if (fromNested !== defaultForStatus(status)) return fromNested;
    }

    if (isObject(body.detail)) {
      const fromPd = messageFromProblemDetail(body.detail, status);
      if (fromPd) return fromPd;
    }

    if (typeof body.detail === "string") {
      const parsedDetail = parseJsonMaybe(body.detail);
      if (isObject(parsedDetail)) {
        const fromPd = messageFromProblemDetail(parsedDetail, status);
        if (fromPd) return fromPd;
      }
      if (looksLikeTimeout(body.detail)) return defaultForStatus(504);
      if (looksLikeUnreachable(body.detail)) return defaultForStatus(503);
      if (
        body.detail.length < 200 &&
        !body.detail.includes("about:blank") &&
        !body.detail.startsWith("{")
      ) {
        return body.detail;
      }
    }

    const fromPd = messageFromProblemDetail(body, status);
    if (fromPd) return fromPd;

    if (typeof body.error === "string" && body.error !== "Assistant BFF returned an error") {
      if (!body.error.includes("BFF")) return body.error;
    }
  }

  if (typeof body === "string") {
    if (looksLikeTimeout(body)) return defaultForStatus(504);
    if (looksLikeUnreachable(body)) return defaultForStatus(503);
    if (body.length < 200 && !body.startsWith("{")) return body;
  }

  return defaultForStatus(status);
}
