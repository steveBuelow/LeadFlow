// src/App.jsx
import { useState } from "react";
import KanbanBoard from "./components/KanbanBoard";

export default function App() {
  const [editingLead, setEditingLead] = useState(null);

  return (
    <div style={{ padding: 28 }}>
      <h2 style={{ marginBottom: 20 }}>⊞ Board</h2>
      <KanbanBoard onEdit={(lead) => setEditingLead(lead)} />

      {/* Edit modal would go here — plug in your existing modal logic */}
      {editingLead && (
        <div>
          <p>Editing: {editingLead.name}</p>
          <button onClick={() => setEditingLead(null)}>Close</button>
        </div>
      )}
    </div>
  );
}