import { Routes, Route, Navigate } from 'react-router-dom';
import { RequireAuth } from './auth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Schedule from './pages/Schedule';
import Waitlist from './pages/Waitlist';
import Patients from './pages/Patients';
import Appointments from './pages/Appointments';
import Communications from './pages/Communications';
import Campaigns from './pages/Campaigns';
import Calls from './pages/Calls';
import Insights from './pages/Insights';
import Simulator from './pages/Simulator';

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
        <Route path="/waitlist" element={<Waitlist />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/communications" element={<Communications />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/calls" element={<Calls />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/simulator" element={<Simulator />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
