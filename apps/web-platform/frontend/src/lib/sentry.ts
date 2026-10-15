const dsn = import.meta.env.VITE_SENTRY_DSN?.trim() || "";

type SentryEvent = {
  event_id: string;
  timestamp: number;
  platform: "javascript";
  level: "error";
  message: string;
  exception: { values: Array<{ type: string; value: string }> };
};

function eventId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

function scrub(value: unknown, max = 500): string {
  const text = value instanceof Error ? value.message : String(value ?? "Unknown error");
  return text.replace(/[\r\n\t]+/g, " ").slice(0, max);
}

function parseDsn(value: string): { publicKey: string; projectId: string; host: string } | null {
  try {
    const url = new URL(value);
    const publicKey = decodeURIComponent(url.username);
    const projectId = url.pathname.replace(/^\/+|\/+$/g, "");
    if (!publicKey || !projectId || !url.hostname) return null;
    return { publicKey, projectId, host: url.origin };
  } catch {
    return null;
  }
}

export function initSentry(): void {
  // The browser reporter is intentionally opt-in and dependency-free.
  // A missing or malformed DSN is treated as disabled configuration.
  if (!dsn || !parseDsn(dsn)) return;
}

export function captureSentryException(error: unknown): void {
  const parsed = parseDsn(dsn);
  if (!parsed) return;

  const id = eventId();
  const event: SentryEvent = {
    event_id: id,
    timestamp: Date.now() / 1000,
    platform: "javascript",
    level: "error",
    message: scrub(error),
    exception: {
      values: [{ type: error instanceof Error ? error.name : "Error", value: scrub(error) }],
    },
  };

  const envelope = [
    JSON.stringify({
      event_id: id,
      sent_at: new Date().toISOString(),
      dsn,
    }),
    JSON.stringify({ type: "event", length: JSON.stringify(event).length }),
    JSON.stringify(event),
  ].join("\n");

  void fetch(`${parsed.host}/api/${parsed.projectId}/envelope/?sentry_version=7&sentry_key=${encodeURIComponent(parsed.publicKey)}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-sentry-envelope" },
    body: envelope,
    keepalive: true,
  }).catch(() => undefined);
}
