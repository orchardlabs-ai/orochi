import { useEffect, useState, type FormEvent } from 'react';
import { api, type Patient } from '../api';

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<Patient[]>('/api/patients')
      .then(setPatients)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const addPatient = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !phone.trim()) return;
    setSaving(true);
    setError('');
    try {
      await api.post<Patient>('/api/patients', { name, phone });
      setName('');
      setPhone('');
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Patients</h1>
          <p className="page-sub">Registered patients and their contact numbers.</p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Add patient</h2>
        </div>
        <form className="inline-form" onSubmit={addPatient}>
          <label className="field">
            <span>Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" required />
          </label>
          <label className="field">
            <span>Phone</span>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+15551234567" required />
          </label>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Add patient'}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>All patients</h2>
          <span className="count-pill">{patients.length}</span>
        </div>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : patients.length === 0 ? (
          <div className="empty">No patients yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.patient_uuid}>
                  <td>{p.name}</td>
                  <td className="mono">{p.phone}</td>
                  <td className="muted">{fmt(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function fmt(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}
