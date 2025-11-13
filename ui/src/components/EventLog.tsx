import React from "react";
import { TerminalIcon } from "../icons";

interface EventLogProps {
  events: string[];
  onClear(): void;
}

export function EventLog({ events, onClear }: EventLogProps) {
  return (
    <div className="event-log">
      <div className="events-toolbar">
        <h2 style={{ display: "flex", alignItems: "center", gap: 10, margin: 0 }}>
          <TerminalIcon width={20} height={20} /> Live Events
        </h2>
        <button type="button" className="ghost" onClick={onClear}>
          Clear Log
        </button>
      </div>
      <textarea readOnly value={events.join("\n")} spellCheck={false} />
    </div>
  );
}
