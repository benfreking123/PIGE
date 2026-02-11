import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { Recipient, ReportSummary } from "../types";

type RecipientFormState = {
  email: string;
  name: string;
  isActive: boolean;
  reportIds: string[];
};

const emptyForm: RecipientFormState = {
  email: "",
  name: "",
  isActive: true,
  reportIds: [],
};

export default function Recipients() {
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [form, setForm] = useState<RecipientFormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const reportNameById = useMemo(() => {
    const index = new Map<string, string>();
    for (const report of reports) {
      index.set(report.report_id, report.name);
    }
    return index;
  }, [reports]);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.getRecipients(), api.getReports()])
      .then(([recipientData, reportData]) => {
        setRecipients(recipientData);
        setReports(reportData);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = (clearMessages = true) => {
    setEditingId(null);
    setForm(emptyForm);
    if (clearMessages) {
      setStatus(null);
      setError(null);
    }
  };

  const startEdit = (recipient: Recipient) => {
    setEditingId(recipient.id);
    setForm({
      email: recipient.email,
      name: recipient.name || "",
      isActive: recipient.is_active,
      reportIds: [...recipient.report_ids],
    });
    setStatus(null);
    setError(null);
  };

  const toggleReport = (reportId: string) => {
    setForm((prev) => {
      const isSelected = prev.reportIds.includes(reportId);
      if (isSelected) {
        return { ...prev, reportIds: prev.reportIds.filter((id) => id !== reportId) };
      }
      return { ...prev, reportIds: [...prev.reportIds, reportId] };
    });
  };

  const save = async () => {
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      if (editingId) {
        await api.updateRecipient(editingId, {
          email: form.email.trim(),
          name: form.name.trim() || null,
          is_active: form.isActive,
        });
        await api.updateRecipientReports(editingId, { report_ids: form.reportIds });
        setStatus("Recipient updated.");
      } else {
        await api.createRecipient({
          email: form.email.trim(),
          name: form.name.trim() || null,
          is_active: form.isActive,
          report_ids: form.reportIds,
        });
        setStatus("Recipient created.");
      }
      load();
      resetForm(false);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (recipient: Recipient) => {
    if (!window.confirm(`Delete recipient ${recipient.email}?`)) return;
    setDeletingId(recipient.id);
    setStatus(null);
    setError(null);
    try {
      await api.deleteRecipient(recipient.id);
      if (editingId === recipient.id) {
        resetForm();
      }
      setStatus("Recipient deleted.");
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <h1>Recipients</h1>
      {error && <div className="card">Error: {error}</div>}
      {status && <div className="card">{status}</div>}

      <div className="card">
        <h3>{editingId ? "Edit recipient" : "Add recipient"}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <label>
            Email
            <input
              style={{ width: "100%" }}
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="name@example.com"
            />
          </label>
          <label>
            Name
            <input
              style={{ width: "100%" }}
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Optional display name"
            />
          </label>
        </div>
        <label style={{ display: "block", marginTop: "10px" }}>
          <input
            type="checkbox"
            checked={form.isActive}
            onChange={(e) => setForm((prev) => ({ ...prev, isActive: e.target.checked }))}
          />{" "}
          Active (receive report emails)
        </label>

        <div style={{ marginTop: "12px" }}>
          <strong>Assigned reports</strong>
          <div style={{ marginTop: "8px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px" }}>
            {reports.map((report) => (
              <label key={report.report_id}>
                <input
                  type="checkbox"
                  checked={form.reportIds.includes(report.report_id)}
                  onChange={() => toggleReport(report.report_id)}
                />{" "}
                {report.name} ({report.report_id})
              </label>
            ))}
            {reports.length === 0 && <div>No reports found.</div>}
          </div>
        </div>

        <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
          <button className="button" onClick={save} disabled={saving}>
            {saving ? "Saving..." : editingId ? "Save recipient" : "Add recipient"}
          </button>
          <button className="button secondary" onClick={resetForm} disabled={saving}>
            Cancel
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Current recipients</h3>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Status</th>
                <th>Assigned reports</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recipients.map((recipient) => (
                <tr key={recipient.id}>
                  <td>{recipient.email}</td>
                  <td>{recipient.name || "-"}</td>
                  <td>{recipient.is_active ? "Active" : "Inactive"}</td>
                  <td>
                    {recipient.report_ids.length > 0
                      ? recipient.report_ids.map((reportId) => reportNameById.get(reportId) || reportId).join(", ")
                      : "-"}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button className="button" onClick={() => startEdit(recipient)}>
                        Edit
                      </button>
                      <button
                        className="button secondary"
                        onClick={() => remove(recipient)}
                        disabled={deletingId === recipient.id}
                      >
                        {deletingId === recipient.id ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {recipients.length === 0 && (
                <tr>
                  <td colSpan={5}>No recipients found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
