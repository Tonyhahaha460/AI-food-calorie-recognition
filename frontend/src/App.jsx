import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import AdminPage from "./pages/AdminPage";
import HomePage from "./pages/HomePage";
import JournalPage from "./pages/JournalPage";
import RecognitionPage from "./pages/RecognitionPage";

function AdminRoute() {
  const { authReady, isWorkMode, openAuthModal } = useAuth();

  if (!authReady) {
    return null;
  }

  if (isWorkMode) {
    return <AdminPage />;
  }

  return (
    <Layout>
      <section className="panel-card">
        <p className="eyebrow">管理權限</p>
        <h1>請先使用管理員帳號登入</h1>
        <p>這個頁面只開放管理員使用。你可以使用示範帳號 `admin / 1234` 登入後再進入行政頁。</p>
        <button type="button" className="primary-button" onClick={() => openAuthModal("login")}>
          前往登入
        </button>
      </section>
    </Layout>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/recognition" element={<RecognitionPage />} />
      <Route path="/journal" element={<JournalPage />} />
      <Route path="/admin" element={<AdminRoute />} />
    </Routes>
  );
}

export default App;
