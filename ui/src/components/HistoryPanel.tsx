import React from "react";
import { HistoryRecord } from "../types";
import { HistoryIcon } from "../icons";

interface HistoryPanelProps {
  history: HistoryRecord[];
}

export function HistoryPanel({ history }: HistoryPanelProps) {
  return (
    <div className="panel">
      <h2>
        <HistoryIcon width={20} height={20} /> Recent Connection History
      </h2>
      <div className="history-list">
        {history.length === 0 ? (
          <div className="history-card">No entries yet. Start monitoring to populate history.</div>
        ) : (
          history.map((entry) => {
            const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "Unknown time";
            return (
              <div key={entry.id} className="history-card">
                <strong>{entry.device || "Unknown"}</strong>
                <span className="meta">{entry.address || "—"}</span>
                <span>{entry.status}</span>
                <span className="meta">{timestamp}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
