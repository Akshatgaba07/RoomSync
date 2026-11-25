import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Landing from "./pages/Landing.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Matches from "./pages/Matches.jsx";
import MatchDetail from "./pages/MatchDetail.jsx";
import Profile from "./pages/Profile.jsx";
import Preferences from "./pages/Preferences.jsx";
import UniversityAdmin from "./pages/UniversityAdmin.jsx";

function Protected({ children, needsProfile = true }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="center muted">Loading…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (needsProfile && !user.profile_complete) return <Navigate to="/onboarding" replace />;
  return children;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/university" element={<UniversityAdmin />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="/onboarding" element={<Protected needsProfile={false}><Onboarding /></Protected>} />
        <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
        <Route path="/matches" element={<Protected><Matches /></Protected>} />
        <Route path="/matches/:id" element={<Protected><MatchDetail /></Protected>} />
        <Route path="/profile" element={<Protected needsProfile={false}><Profile /></Protected>} />
        <Route path="/preferences" element={<Protected><Preferences /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
