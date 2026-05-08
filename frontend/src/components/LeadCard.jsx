import { useState } from "react";

export default function LeadCard({ lead, onEdit, onDelete }) {
  const [confirming, setConfirming] = useState(false);

  return (
    <div style={{
      background: "var(--surface2)",
      borderRadius: "var(--radius-sm)",
      padding: "12px 13px",
      marginBottom: "7px",
      borderLeft: "2px solid transparent",
      cursor: "grab",
    }}>
      <div style={{ fontWeight: 600, fontSize: 13 }}>{lead.name}</div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
        {lead.source || "—"}
      </div>
      {lead.message && (
        <div style={{ fontSize: 11, color: "var(--text-subtle)", marginTop: 5, lineHeight: 1.45 }}>
          {lead.message.length > 60 ? lead.message.slice(0, 60) + "…" : lead.message}
        </div>
      )}
      {lead.notes && (
        <div style={{ fontSize: 11, color: "var(--text-subtle)", marginTop: 4, fontStyle: "italic" }}>
          📝 {lead.notes}
        </div>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <CardBtn color="var(--violet)" onClick={() => onEdit(lead)}>✎ Edit</CardBtn>
        {confirming ? (
          <>
            <CardBtn color="var(--rose)" onClick={() => onDelete(lead.id)}>Sure?</CardBtn>
            <CardBtn color="var(--text-muted)" onClick={() => setConfirming(false)}>Cancel</CardBtn>
          </>
        ) : (
          <CardBtn color="var(--rose)" onClick={() => setConfirming(true)}>✕ Delete</CardBtn>
        )}
      </div>
    </div>
  );
}

function CardBtn({ color, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 11, padding: "2px 8px", borderRadius: 5,
        border: `1px solid ${color}22`, background: `${color}11`,
        color, cursor: "pointer", fontWeight: 700, transition: "opacity 0.15s",
      }}
    >
      {children}
    </button>
  );
}