import { useEffect, useState } from 'react';
import './Toast.css';

export type ToastVariant = 'default' | 'call';

export interface ToastOptions {
  title: string;
  subtitle?: string;
  variant?: ToastVariant;
  /** milliseconds before auto-dismiss; defaults to 3200 */
  duration?: number;
}

interface ToastItem extends ToastOptions {
  id: number;
}

// --- Self-contained event emitter (no external state lib) ---
type Listener = (t: ToastItem) => void;
const listeners = new Set<Listener>();
let seq = 0;

/** Imperative trigger — call from anywhere to raise a toast. */
export function showToast(options: ToastOptions): number {
  const item: ToastItem = { id: ++seq, ...options };
  listeners.forEach((l) => l(item));
  return item.id;
}

/** Convenience helper for the "incoming call" variant. */
export function showIncomingCall(title: string, subtitle?: string, duration?: number): number {
  return showToast({ title, subtitle, variant: 'call', duration });
}

function PhoneGlyph() {
  return (
    <span className="toast-glyph" aria-hidden="true">
      <span className="toast-glyph-ring" />
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.9.36 1.78.7 2.62a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.46-1.27a2 2 0 0 1 2.11-.45c.84.34 1.72.57 2.62.7A2 2 0 0 1 22 16.92z" />
      </svg>
    </span>
  );
}

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const duration = item.duration ?? 3200;
    const hide = window.setTimeout(() => setLeaving(true), duration);
    const remove = window.setTimeout(() => onDismiss(item.id), duration + 260);
    return () => {
      window.clearTimeout(hide);
      window.clearTimeout(remove);
    };
  }, [item, onDismiss]);

  return (
    <div
      className={`toast toast-${item.variant ?? 'default'}${leaving ? ' toast-leaving' : ''}`}
      role="status"
      aria-live="polite"
      onClick={() => setLeaving(true)}
    >
      {item.variant === 'call' && <PhoneGlyph />}
      <div className="toast-body">
        <div className="toast-title">{item.title}</div>
        {item.subtitle && <div className="toast-subtitle">{item.subtitle}</div>}
      </div>
    </div>
  );
}

/** Mount once (e.g. in Layout). Renders all active toasts. */
export default function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    const listener: Listener = (t) => setItems((prev) => [...prev, t]);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="toast-host" aria-live="polite">
      {items.map((item) => (
        <ToastCard key={item.id} item={item} onDismiss={dismiss} />
      ))}
    </div>
  );
}
