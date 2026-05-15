import { NextResponse } from "next/server";

import { formatUserFacingError } from "@/lib/api-errors";

const DEFAULT_BFF = "http://localhost:8080";

function bffBaseUrl(): string {
  return (process.env.BFF_BASE_URL ?? DEFAULT_BFF).replace(/\/$/, "");
}

export async function GET() {
  const bffUrl = `${bffBaseUrl()}/api/v1/ingest/catalog`;
  try {
    const upstream = await fetch(bffUrl, {
      headers: { Accept: "application/json" },
      cache: "no-store",
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
        { message: formatUserFacingError(upstream.status, detail) },
        { status: upstream.status },
      );
    }
    return NextResponse.json(JSON.parse(text));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { message: formatUserFacingError(502, message) },
      { status: 502 },
    );
  }
}
