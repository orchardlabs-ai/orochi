export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(path, {
    method,
    credentials: 'include',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = data.detail || data.message || message;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};

// ---- Shared types ----
export interface User {
  email: string;
}

export interface Patient {
  patient_uuid: string;
  name: string;
  phone: string;
  created_at: string;
}

export interface Appointment {
  appointment_id: string;
  patient_uuid: string;
  patient_name?: string;
  datetime: string;
  location: string;
  status: 'scheduled' | 'confirmed' | 'cancelled';
  created_at: string;
}

export interface Call {
  call_uuid: string;
  patient_uuid: string;
  patient_name?: string;
  direction: 'inbound' | 'outbound';
  status: string;
  started_at: string;
  ended_at?: string;
}

export interface TranscriptTurn {
  role: string;
  text: string;
}

export interface SimulateInboundResult {
  call: Call & { transcript?: TranscriptTurn[] };
  actions: string[];
  appointment?: Appointment;
}

export interface ReminderResult {
  appointment_id: string;
  script: string;
  call_uuid: string;
}

export interface ScheduleData {
  open: string;
  close: string;
  slot_minutes: number;
  weekdays: string[];
  slots: string[];
  availability: Record<string, string[]>;
}
