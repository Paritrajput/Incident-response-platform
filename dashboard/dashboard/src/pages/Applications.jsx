import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { applicationsApi } from "../services/api";
import { useApplications } from "../context/ApplicationContext";

export default function Applications() {
  const navigate = useNavigate();
  const { applications, selectedApplication, setSelectedApplication, refreshApplications, loadingApplications } = useApplications();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function createApplication(event) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError("");
    try {
      const app = await applicationsApi.create({ name: name.trim(), description: description.trim() });
      await refreshApplications();
      setSelectedApplication(app);
      setName("");
      setDescription("");
      navigate("/onboarding");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function renameApplication(applicationId) {
    if (!editingName.trim()) return;
    setSaving(true);
    setError("");
    try {
      await applicationsApi.update(applicationId, { name: editingName.trim() });
      setEditingId(null);
      await refreshApplications();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteApplication(application) {
    if (!window.confirm(`Delete ${application.name}? This cannot be undone.`)) return;
    setSaving(true);
    setError("");
    try {
      await applicationsApi.remove(application.id);
      if (selectedApplication?.id === application.id) setSelectedApplication(null);
      await refreshApplications();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <Navbar showLinks={false} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Applications</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Choose the service group you want IncidentAI to monitor.</p>
        </div>

        <form onSubmit={createApplication} className="card mb-8 grid gap-4 p-6 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <div>
            <label className="label">Application name</label>
            <input className="input" value={name} onChange={(event) => setName(event.target.value)} placeholder="Payments API" />
          </div>
          <div>
            <label className="label">Description <span className="text-[var(--text-muted)]">(optional)</span></label>
            <input className="input" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Production payment services" />
          </div>
          <button className="btn-primary" disabled={saving || !name.trim()}>{saving ? "Creating..." : "Create application"}</button>
        </form>

        {error && <p className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">{error}</p>}

        {loadingApplications ? (
          <div className="card p-12 text-center text-sm text-[var(--text-secondary)]">Loading applications...</div>
        ) : applications.length === 0 ? (
          <div className="card p-12 text-center">
            <h2 className="text-xl font-bold text-[var(--text-primary)]">Create your first application</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">Applications keep integrations, incidents, and deploy history isolated.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {applications.map((application) => (
              <div key={application.id} className={`card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between ${selectedApplication?.id === application.id ? "border-[var(--accent)]" : ""}`}>
                <div className="min-w-0">
                  {editingId === application.id ? (
                    <div className="flex gap-2">
                      <input className="input" value={editingName} onChange={(event) => setEditingName(event.target.value)} autoFocus />
                      <button className="btn-primary" onClick={() => renameApplication(application.id)} disabled={saving}>Save</button>
                    </div>
                  ) : (
                    <>
                      <h2 className="truncate font-semibold text-[var(--text-primary)]">{application.name}</h2>
                      {application.description && <p className="mt-1 text-sm text-[var(--text-secondary)]">{application.description}</p>}
                    </>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="badge bg-[var(--bg-subtle)] text-[var(--text-secondary)]">{application.status || "draft"}</span>
                  <button className="btn-secondary" onClick={() => { setSelectedApplication(application); navigate("/dashboard"); }}>Open</button>
                  <button className="btn-secondary" onClick={() => { setEditingId(application.id); setEditingName(application.name); }}>Rename</button>
                  <button className="btn-secondary text-red-500" onClick={() => deleteApplication(application)} disabled={saving}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
