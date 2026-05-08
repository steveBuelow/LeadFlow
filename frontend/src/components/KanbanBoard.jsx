// src/components/KanbanBoard.jsx
import { useEffect, useState } from "react";
import { DragDropContext } from "@hello-pangea/dnd";
import API from "../services/api";
import KanbanColumn from "./KanbanColumn";

const STATUSES = ["New", "Contacted", "Qualified", "Closed"];

export default function KanbanBoard({ onEdit }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    API.get("/leads")
      .then((res) => setLeads(res.data.leads || []))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("Remove this lead?")) return;
    const backup = [...leads];
    setLeads((prev) => prev.filter((l) => l.id !== id));
    try {
      await API.delete("/remove-lead", { data: { id } });
    } catch {
      setLeads(backup);   // revert on failure
    }
  };

  const handleDragEnd = async (result) => {
    const { draggableId, destination } = result;
    if (!destination) return;

    const newStatus = destination.droppableId;
    const leadId    = parseInt(draggableId);
    const lead      = leads.find((l) => l.id === leadId);
    if (!lead || lead.status === newStatus) return;

    // Optimistic update
    const oldStatus = lead.status;
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
    );

    try {
      await API.put("/update-lead", {
        id: lead.id,
        name: lead.name,
        source: lead.source,
        message: lead.message,
        status: newStatus,
        notes: lead.notes,
      });
    } catch {
      // Revert if server rejects
      setLeads((prev) =>
        prev.map((l) => (l.id === leadId ? { ...l, status: oldStatus } : l))
      );
    }
  };

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
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