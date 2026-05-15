import { randomUUID } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import { formatUserFacingError } from "@/lib/api-errors";

const DEFAULT_BFF = "http://localhost:8080";
const BFF_INGEST_TIMEOUT_MS = 360_000;

function bffBaseUrl(): string {
  return (process.env.BFF_BASE_URL ?? DEFAULT_BFF).replace(/\/$/, "");
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const correlationId =
    req.headers.get("x-correlation-id")?.trim() || randomUUID();
  const bffUrl = `${bffBaseUrl()}/api/v1/ingest/run`;

  try {
    const upstream = await fetch(bffUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Correlation-Id": correlationId,
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(BFF_INGEST_TIMEOUT_MS),
    });
    const text = await upstream.text();
    if (!upstream.ok) {
      let detail: unknown = text;
      try {
        detail = JSON.parse(text);
      } catch {
        /* raw */
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
    return NextResponse.json(JSON.parse(text), {
      headers: { "X-Correlation-Id": correlationId },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "Could not reach BFF", detail: message, bffUrl },
      { status: 502 },
    );
  }
}
