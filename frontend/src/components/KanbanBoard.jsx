// src/components/KanbanBoard.jsx
import { useEffect, useState } from "react";
import { DragDropContext } from "@hello-pangea/dnd";
import API from "../services/api";
import KanbanColumn from "./KanbanColumn";

const STATUSES = ["New", "Contacted", "Qualified", "Closed"];

export default function KanbanBoard({ onEdit }) {
  const [leads,   setLeads]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    API.get("/leads")
      .then((res) => setLeads(res.data.leads || []))
      .catch(() => setError("Failed to load leads. Please refresh."))
      .finally(() => setLoading(false));
  }, []);

  // ── FIX: removed confirm() — LeadCard already shows an inline
  //         "Sure? / Cancel" confirmation before calling onDelete.
  //         Having confirm() here meant the user was asked twice.
  const handleDelete = async (id) => {
    const backup = [...leads];
    setLeads((prev) => prev.filter((l) => l.id !== id));
    try {
      await API.delete("/remove-lead", { data: { id } });
    } catch {
      setLeads(backup); // revert on network/server failure
    }
  };

  const handleDragEnd = async (result) => {
    const { draggableId, destination } = result;
    if (!destination) return;

    const newStatus = destination.droppableId;
    const leadId    = parseInt(draggableId, 10);
    const lead      = leads.find((l) => l.id === leadId);
    if (!lead || lead.status === newStatus) return;

    const oldStatus = lead.status;
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
    );

    try {
      await API.put("/update-lead", {
        id:      lead.id,
        name:    lead.name,
        source:  lead.source  ?? "",
        message: lead.message ?? "",
        status:  newStatus,
        notes:   lead.notes   ?? "",
      });
    } catch {
      // Revert optimistic update on failure
      setLeads((prev) =>
        prev.map((l) => (l.id === leadId ? { ...l, status: oldStatus } : l))
      );
    }
  };

  if (loading) {
    return (
      <p style={{ color: "var(--text-muted)", padding: "40px 0", textAlign: "center" }}>
        Loading…
      </p>
    );
  }

  if (error) {
    return (
      <p style={{ color: "var(--rose)", padding: "40px 0", textAlign: "center" }}>
        {error}
      </p>
    );
  }

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
        {STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            leads={leads.filter((l) => l.status === status)}
            onEdit={onEdit}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </DragDropContext>
  );
}