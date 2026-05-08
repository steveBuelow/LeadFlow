// src/components/LeadCard.jsx
export default function LeadCard({ lead, onEdit, onDelete }) {
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
        <div style={{ fontSize: 11, color: "var(--text-subtle)", marginTop: 5 }}>
          {lead.message.length > 60
            ? lead.message.slice(0, 60) + "…"
            : lead.message}
        </div>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <button onClick={() => onEdit(lead)} style={btnStyle("var(--violet)")}>Edit</button>
        <button onClick={() => onDelete(lead.id)} style={btnStyle("var(--rose)")}>✕</button>
      </div>
    </div>
  );
}

function btnStyle(color) {
  return {
    fontSize: 11, padding: "2px 8px", borderRadius: 5, border: "none",
    background: "transparent", color, cursor: "pointer", fontWeight: 700,
  };
}