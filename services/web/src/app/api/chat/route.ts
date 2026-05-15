import { randomUUID } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import type { AssistChatRequest, AssistChatResponse } from "@/lib/chat-types";

const DEFAULT_BFF = "http://localhost:8080";

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
    });
  } catch (err) {
    const messageText =
      err instanceof Error ? err.message : "Unknown fetch error";
    return NextResponse.json(
      {
        error: "Could not reach assistant BFF",
        detail: messageText,
        bffUrl,
      },
      { status: 502 },
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
        error: "Assistant BFF returned an error",
        status: upstream.status,
        detail,
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
