"use client";

import { useState } from "react";

import { ChatWindow } from "@/components/ChatWindow";
import { IngestPanel } from "@/components/IngestPanel";

import styles from "./AppShell.module.css";

export type AppTab = "chat" | "ingest";

export function AppShell() {
  const [tab, setTab] = useState<AppTab>("chat");

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.topBar}>
          <div className={styles.brand}>
            <div className={styles.brandLogo} aria-hidden>
              AI
            </div>
            <p className={styles.brandTitle}>Search Assistant</p>
          </div>
          <nav className={styles.tabs} aria-label="Main">
            <button
              type="button"
              className={`${styles.tab} ${tab === "chat" ? styles.tabActive : ""}`}
              onClick={() => setTab("chat")}
              aria-current={tab === "chat" ? "page" : undefined}
            >
              Chat
            </button>
            <button
              type="button"
              className={`${styles.tab} ${tab === "ingest" ? styles.tabActive : ""}`}
              onClick={() => setTab("ingest")}
              aria-current={tab === "ingest" ? "page" : undefined}
            >
              Ingest
            </button>
          </nav>
        </header>
        <main className={styles.panel}>
          {tab === "chat" ? <ChatWindow embedded /> : <IngestPanel />}
        </main>
      </div>
    </div>
  );
}
