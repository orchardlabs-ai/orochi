import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../api';
import './Insurance.css';

type Patient = {
  patient_uuid: string;
  name: string;
  phone?: string;
};

type InsuranceOnFile = {
  patient_uuid: string;
  payer: string;
  member_id: string;
  updated_at?: string;
};

type CoverageLine = {
  service: string;
  covered_pct: number;
};

type Verification = {
  eligible: boolean;
  payer: string;
  member_id: string;
  plan?: string | null;
  group?: string | null;
  copay: number;
  deductible_remaining: number;
  coverage: CoverageLine[];
  verified_at: string;
  status: string;
};

type InsuranceState = {
  insurance_on_file: InsuranceOnFile | null;
  last_verification: Verification | null;
};

const PAYERS = [
  'Delta Dental',
  'Cigna',
  'Aetna',
  'MetLife',
  'Guardian',
  'UnitedHealthcare',
  'Blue Cross Blue Shield',
];

export default function Insurance() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientUuid, setPatientUuid] = useState('');
  const [state, setState] = useState<InsuranceState | null>(null);

  const [payer, setPayer] = useState('');
  const [memberId, setMemberId] = useState('');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<Patient[]>('/api/patients')
      .then(setPatients)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const loadInsurance = (uuid: string) => {
    if (!uuid) {
      setState(null);
      return;
    }
    setError('');
    api
      .get<InsuranceState>(`/api/insurance/${uuid}`)
      .then((s) => {
        setState(s);
        setPayer(s.insurance_on_file?.payer || '');
        setMemberId(s.insurance_on_file?.member_id || '');
      })
      .catch((e) => setError((e as Error).message));
  };

  const onPickPatient = (uuid: string) => {
    setPatientUuid(uuid);
    setState(null);
    setPayer('');
    setMemberId('');
    loadInsurance(uuid);
  };

  const saveOnFile = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientUuid || !payer.trim() || !memberId.trim()) return;
    setSaving(true);
    setError('');
    try {
      await api.post<InsuranceOnFile>(`/api/insurance/${patientUuid}`, {
        payer: payer.trim(),
        member_id: memberId.trim(),
      });
      loadInsurance(patientUuid);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const runVerify = async () => {
    if (!patientUuid) return;
    setVerifying(true);
    setError('');
    try {
      const res = await api.post<Verification>(
        `/api/insurance/${patientUuid}/verify`,
        { payer: payer.trim() || undefined, member_id: memberId.trim() || undefined }
      );
      setState((prev) =>
        prev
          ? { ...prev, last_verification: res }
          : { insurance_on_file: null, last_verification: res }
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setVerifying(false);
    }
  };

  const v = state?.last_verification || null;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Insurance</h1>
          <p className="page-sub">
            Capture insurance on file and verify eligibility during the call.
          </p>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Patient</h2>
        </div>
        {loading ? (
          <div className="empty">Loading patients…</div>
        ) : (
          <div className="field">
            <label htmlFor="ins-patient">Select a patient</label>
            <select
              id="ins-patient"
              value={patientUuid}
              onChange={(e) => onPickPatient(e.target.value)}
            >
              <option value="">— choose —</option>
              {patients.map((p) => (
                <option key={p.patient_uuid} value={p.patient_uuid}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>

      {patientUuid && (
        <section className="panel">
          <div className="panel-head">
            <h2>Insurance on file</h2>
            {state?.insurance_on_file && (
              <span className="badge">On file</span>
            )}
          </div>
          <form className="stacked-form" onSubmit={saveOnFile}>
            <div className="field">
              <label htmlFor="ins-payer">Payer</label>
              <input
                id="ins-payer"
                list="ins-payers"
                value={payer}
                onChange={(e) => setPayer(e.target.value)}
                placeholder="e.g. Delta Dental"
              />
              <datalist id="ins-payers">
                {PAYERS.map((p) => (
                  <option key={p} value={p} />
                ))}
              </datalist>
            </div>
            <div className="field">
              <label htmlFor="ins-member">Member ID</label>
              <input
                id="ins-member"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                placeholder="e.g. XYZ123456789"
              />
            </div>
            <div className="insurance-actions">
              <button
                type="submit"
                className="btn btn-secondary"
                disabled={saving || !payer.trim() || !memberId.trim()}
              >
                {saving ? 'Saving…' : 'Save on file'}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={runVerify}
                disabled={verifying || !payer.trim() || !memberId.trim()}
              >
                {verifying ? 'Verifying…' : 'Verify eligibility'}
              </button>
            </div>
          </form>
        </section>
      )}

      {v && (
        <section className="panel">
          <div className="panel-head">
            <h2>Eligibility result</h2>
            <span
              className={`badge ${
                v.eligible ? 'insurance-badge-ok' : 'insurance-badge-bad'
              }`}
            >
              {v.eligible ? 'Eligible' : 'Inactive'}
            </span>
          </div>

          <div className="result-card">
            <div className="kv-grid">
              <div>
                <span className="small muted">Payer</span>
                <div>{v.payer}</div>
              </div>
              <div>
                <span className="small muted">Member ID</span>
                <div className="mono">{v.member_id}</div>
              </div>
              <div>
                <span className="small muted">Plan</span>
                <div>{v.plan || '—'}</div>
              </div>
              <div>
                <span className="small muted">Group</span>
                <div className="mono">{v.group || '—'}</div>
              </div>
              <div>
                <span className="small muted">Copay</span>
                <div>{v.eligible ? `$${v.copay}` : '—'}</div>
              </div>
              <div>
                <span className="small muted">Deductible remaining</span>
                <div>{v.eligible ? `$${v.deductible_remaining}` : '—'}</div>
              </div>
            </div>

            {v.eligible && v.coverage.length > 0 && (
              <table className="table insurance-coverage">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Covered</th>
                  </tr>
                </thead>
                <tbody>
                  {v.coverage.map((c) => (
                    <tr key={c.service}>
                      <td>{c.service}</td>
                      <td>{c.covered_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {!v.eligible && (
              <p className="insurance-inactive-note muted">
                This member came back inactive. Confirm the member ID and payer,
                or collect updated coverage details.
              </p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
