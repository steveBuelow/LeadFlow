// src/components/KanbanColumn.jsx
import { Droppable, Draggable } from "@hello-pangea/dnd";
import LeadCard from "./LeadCard";

const COLORS = {
  New: "var(--accent)",
  Contacted: "var(--amber)",
  Qualified: "var(--violet)",
  Closed: "var(--text-muted)",
};

export default function KanbanColumn({ status, leads, onEdit, onDelete }) {
  const color = COLORS[status] || "var(--accent)";

  return (
    <div style={{
      background: "var(--surface)",
      borderRadius: "var(--radius)",
      borderTop: `2px solid ${color}`,
      minHeight: 220,
      flex: 1,
    }}>
      {/* Column header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 13px", borderBottom: "1px solid var(--border)",
      }}>
        <span style={{ fontWeight: 700, fontSize: 11, color, textTransform: "uppercase" }}>
          ● {status}
        </span>
        <span style={{
          fontSize: 11, background: "var(--surface2)", color: "var(--text-muted)",
          padding: "1px 8px", borderRadius: 20,
        }}>
          {leads.length}
        </span>
      </div>

      {/* Droppable card area */}
      <Droppable droppableId={status}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            style={{
              padding: 10,
              minHeight: 80,
              background: snapshot.isDraggingOver ? "var(--surface2)" : "transparent",
              transition: "background 0.15s",
            }}
          >
            {leads.length === 0 && (
              <p style={{ fontSize: 12, color: "var(--text-subtle)", textAlign: "center", padding: "24px 10px" }}>
                Drop leads here
              </p>
            )}
            {leads.map((lead, index) => (
              <Draggable key={String(lead.id)} draggableId={String(lead.id)} index={index}>
                {(provided) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                  >
                    <LeadCard lead={lead} onEdit={onEdit} onDelete={onDelete} />
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  );
}