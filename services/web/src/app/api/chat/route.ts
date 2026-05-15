import { randomUUID } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import { formatUserFacingError } from "@/lib/api-errors";
import type { AssistChatRequest, AssistChatResponse } from "@/lib/chat-types";

const DEFAULT_BFF = "http://localhost:8080";
/** Slightly above BFF → ai-core timeout so the proxy does not abort first. */
const BFF_CHAT_TIMEOUT_MS = 360_000;

function bffBaseUrl(): string {
  return (process.env.BFF_BASE_URL ?? DEFAULT_BFF).replace(/\/$/, "");
}

/**
 * Server-side proxy to the Spring BFF so the browser never needs CORS credentials
 * to `localhost:8080`, and the internal BFF URL can differ in Docker.
 */
export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("message" in body) ||
    typeof (body as { message: unknown }).message !== "string"
  ) {
    return NextResponse.json(
      { error: "Expected JSON object with string field `message`" },
      { status: 400 },
    );
  }

  const { message, session_id, structured_output } = body as Record<
    string,
    unknown
  >;

  const payload: AssistChatRequest = {
    message: String(message).trim(),
    ...(typeof session_id === "string" && session_id
      ? { session_id: session_id.slice(0, 128) }
      : {}),
    structured_output:
      typeof structured_output === "boolean" ? structured_output : false,
  };

  if (!payload.message) {
    return NextResponse.json({ error: "message must not be empty" }, { status: 400 });
  }

  const correlationId =
    req.headers.get("x-correlation-id")?.trim() || randomUUID();

  const bffUrl = `${bffBaseUrl()}/api/v1/assist/chat`;
  let upstream: Response;
  try {
    upstream = await fetch(bffUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Correlation-Id": correlationId,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(BFF_CHAT_TIMEOUT_MS),
    });
  } catch (err) {
    const timedOut =
      err instanceof Error &&
      (err.name === "TimeoutError" || err.name === "AbortError");
    return NextResponse.json(
      {
        message: timedOut
          ? formatUserFacingError(504, null)
          : "Could not reach the assistant. Check that the backend is running.",
      },
      { status: timedOut ? 504 : 502 },
    );
  }

  const text = await upstream.text();
  if (!upstream.ok) {
    let detail: unknown = text;
    try {
      detail = JSON.parse(text);
    } catch {
      /* keep raw text */
    }
    return NextResponse.json(
      {
        message: formatUserFacingError(
          upstream.status >= 400 ? upstream.status : 502,
          detail,
        ),
      },
      { status: upstream.status >= 400 ? upstream.status : 502 },
    );
  }

  let data: AssistChatResponse;
  try {
    data = JSON.parse(text) as AssistChatResponse;
  } catch {
    return NextResponse.json(
      { error: "BFF returned invalid JSON", raw: text.slice(0, 500) },
      { status: 502 },
    );
  }

  return NextResponse.json(data, {
    status: 200,
    headers: {
      "X-Correlation-Id": data.correlation_id ?? correlationId,
    },
  });
}
