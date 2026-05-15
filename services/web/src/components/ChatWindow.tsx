"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { formatUserFacingError } from "@/lib/api-errors";
import type { AssistChatResponse } from "@/lib/chat-types";

import styles from "./ChatWindow.module.css";

type Role = "user" | "assistant" | "system";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  meta?: {
    correlationId?: string;
    graphPath?: string;
    citations?: AssistChatResponse["citations"];
    structured?: Record<string, unknown> | null;
  };
};

const SESSION_KEY = "ai-search-assistant-session-id";

const SUGGESTIONS = [
  "Summarize the main topics in my uploaded documents.",
  "What policies or procedures are described in the indexed content?",
  "List the key requirements or recommendations from my documents.",
] as const;

function readOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

type ChatWindowProps = {
  /** When true, omit outer shell/header (used inside AppShell tabs). */
  embedded?: boolean;
};

export function ChatWindow({ embedded = false }: ChatWindowProps) {
  const formId = useId();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [structuredOutput, setStructuredOutput] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sessionIdRef = useRef("");

  useEffect(() => {
    sessionIdRef.current = readOrCreateSessionId();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;

      setError(null);
      setInput("");
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      };
      setMessages((m) => [...m, userMsg]);
      setPending(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            session_id: sessionIdRef.current || undefined,
            structured_output: structuredOutput,
          }),
        });

        const corr = res.headers.get("x-correlation-id") ?? undefined;

        if (!res.ok) {
          const errText = await res.text();
          let payload: unknown = errText;
          try {
            payload = JSON.parse(errText) as unknown;
          } catch {
            /* use raw text */
          }
          const friendly =
            typeof payload === "object" &&
            payload !== null &&
            "message" in payload &&
            typeof (payload as { message: unknown }).message === "string"
              ? (payload as { message: string }).message
              : formatUserFacingError(res.status, payload);
          throw new Error(friendly);
        }

        const data = (await res.json()) as AssistChatResponse;
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.answer_text || "(Empty response)",
          meta: {
            correlationId: data.correlation_id ?? corr,
            graphPath: data.graph_path,
            citations: data.citations ?? [],
            structured: data.structured,
          },
        };
        setMessages((m) => [...m, assistantMsg]);
      } catch (e) {
        const msg =
          e instanceof Error
            ? e.message
            : "Something went wrong. Please try again.";
        setError(msg);
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: msg,
          },
        ]);
      } finally {
        setPending(false);
      }
    },
    [pending, structuredOutput],
  );

  const send = useCallback(() => {
    void sendMessage(input);
  }, [input, sendMessage]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div
      className={
        embedded ? `${styles.shell} ${styles.shellEmbedded}` : styles.shell
      }
    >
      <div
        className={
          embedded ? `${styles.app} ${styles.appEmbedded}` : styles.app
        }
      >
        {!embedded && (
          <header className={styles.header}>
            <div className={styles.logo} aria-hidden>
              AI
            </div>
            <div className={styles.headerText}>
              <h1 className={styles.title}>Assistant</h1>
              <p className={styles.subtitle}>
                Answers grounded in your document libraries — with sources cited.
              </p>
              <span className={styles.status}>
                <span className={styles.statusDot} aria-hidden />
                Ready
              </span>
            </div>
          </header>
        )}

        <div
          className={styles.messages}
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {messages.length === 0 && !pending && (
            <EmptyState
              disabled={pending}
              onPick={(q) => void sendMessage(q)}
            />
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {pending && <TypingIndicator />}
          <div ref={endRef} />
        </div>

        <footer className={styles.composer}>
          {error && (
            <p className={styles.alert} role="alert">
              {error}
            </p>
          )}
          <form id={formId} onSubmit={onSubmit}>
            <div className={styles.inputWrap}>
              <label htmlFor={`${formId}-msg`} className="sr-only">
                Message
              </label>
              <textarea
                ref={textareaRef}
                id={`${formId}-msg`}
                className={styles.textarea}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask a question…"
                rows={1}
                disabled={pending}
                aria-describedby={`${formId}-hint`}
              />
              <div className={styles.composerActions}>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    checked={structuredOutput}
                    disabled={pending}
                    onChange={(e) => setStructuredOutput(e.target.checked)}
                  />
                  Structured
                </label>
                <button
                  type="submit"
                  className={styles.sendBtn}
                  disabled={pending || !input.trim()}
                >
                  {pending ? "Sending…" : "Send"}
                </button>
              </div>
            </div>
            <p id={`${formId}-hint`} className={styles.hint}>
              Enter to send · Shift+Enter for a new line
            </p>
          </form>
        </footer>
      </div>
    </div>
  );
}

function EmptyState({
  disabled,
  onPick,
}: {
  disabled: boolean;
  onPick: (text: string) => void;
}) {
  return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon} aria-hidden>
        ✦
      </div>
      <h2 className={styles.emptyTitle}>How can I help?</h2>
      <p className={styles.emptyHint}>
        Ask anything about your allowed documents. I will search the corpus and
        cite the sources I use.
      </p>
      <div className={styles.suggestions}>
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            className={styles.suggestionBtn}
            disabled={disabled}
            onClick={() => onPick(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div
      className={styles.typing}
      aria-busy="true"
      aria-label="Assistant is thinking"
    >
      <div className={`${styles.avatar} ${styles.avatarAssistant}`} aria-hidden>
        AI
      </div>
      <div className={styles.typingBubble}>
        <span className={styles.typingDot} />
        <span className={styles.typingDot} />
        <span className={styles.typingDot} />
      </div>
    </div>
  );
}

function MessageBubble({ message: m }: { message: ChatMessage }) {
  const isUser = m.role === "user";
  const isSystem = m.role === "system";
  const citations = m.meta?.citations?.filter(Boolean) ?? [];
  const [citationsOpen, setCitationsOpen] = useState(false);

  const rowClass = [
    styles.messageRow,
    isUser && styles.messageRowUser,
    m.role === "assistant" && styles.messageRowAssistant,
    isSystem && styles.messageRowSystem,
  ]
    .filter(Boolean)
    .join(" ");

  const avatarClass = [
    styles.avatar,
    isUser && styles.avatarUser,
    m.role === "assistant" && styles.avatarAssistant,
    isSystem && styles.avatarSystem,
  ]
    .filter(Boolean)
    .join(" ");

  const bubbleClass = [
    styles.bubble,
    isUser && styles.bubbleUser,
    m.role === "assistant" && styles.bubbleAssistant,
    isSystem && styles.bubbleSystem,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={rowClass}>
      <div className={avatarClass} aria-hidden>
        {isUser ? "You" : isSystem ? "!" : "AI"}
      </div>
      <div className={bubbleClass}>
        {m.content}
        {citations.length > 0 && (
          <div className={styles.citations}>
            <button
              type="button"
              className={styles.citationsToggle}
              onClick={() => setCitationsOpen((o) => !o)}
              aria-expanded={citationsOpen}
            >
              <span>
                {citations.length} source{citations.length === 1 ? "" : "s"}
              </span>
              <span aria-hidden>{citationsOpen ? "▲" : "▼"}</span>
            </button>
            {citationsOpen && (
              <ul className={styles.citationList}>
                {citations.map((c) => (
                  <li
                    key={`${c.document_id}-${c.library_id}`}
                    className={styles.citationCard}
                  >
                    <span className={styles.citationTitle}>{c.title}</span>
                    <span className={styles.citationId}>{c.document_id}</span>
                    {c.snippet ? (
                      <p className={styles.citationSnippet}>
                        {c.snippet.length > 280
                          ? `${c.snippet.slice(0, 280)}…`
                          : c.snippet}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {m.meta?.structured && Object.keys(m.meta.structured).length > 0 && (
          <details className={styles.citations}>
            <summary className={styles.citationsToggle}>Structured data</summary>
            <pre className={styles.structuredPre}>
              {JSON.stringify(m.meta.structured, null, 2)}
            </pre>
          </details>
        )}
        {(m.meta?.correlationId || m.meta?.graphPath) && (
          <footer className={styles.meta}>
            {m.meta.correlationId ? (
              <span className={styles.metaTag} title={m.meta.correlationId}>
                {m.meta.correlationId.slice(0, 8)}…
              </span>
            ) : null}
            {m.meta.graphPath ? (
              <span className={styles.metaTag}>{m.meta.graphPath}</span>
            ) : null}
          </footer>
        )}
      </div>
    </article>
  );
}
