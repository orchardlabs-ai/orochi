import { Routes, Route, Navigate } from 'react-router-dom';
import { RequireAuth } from './auth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Schedule from './pages/Schedule';
import Catalog from './pages/Catalog';
import Waitlist from './pages/Waitlist';
import Patients from './pages/Patients';
import Appointments from './pages/Appointments';
import Communications from './pages/Communications';
import Reminders from './pages/Reminders';
import Campaigns from './pages/Campaigns';
import Escalations from './pages/Escalations';
import Insurance from './pages/Insurance';
import Calls from './pages/Calls';
import Insights from './pages/Insights';
import Simulator from './pages/Simulator';
import Demo from './pages/Demo';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/waitlist" element={<Waitlist />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/escalations" element={<Escalations />} />
        <Route path="/communications" element={<Communications />} />
        <Route path="/reminders" element={<Reminders />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/insurance" element={<Insurance />} />
        <Route path="/calls" element={<Calls />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/simulator" element={<Simulator />} />
        <Route path="/demo" element={<Demo />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
