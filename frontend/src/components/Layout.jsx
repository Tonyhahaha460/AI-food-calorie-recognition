import { Link } from "react-router-dom";
import MemberAuthModal from "./MemberAuthModal";
import ModeControls from "./ModeControls";

function Layout({ children }) {
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link to="/" className="brand-mark">
          AI Meal Scanner
        </Link>
        <nav className="site-nav">
          <Link to="/">首頁</Link>
          <Link to="/recognition">掃描</Link>
          <Link to="/journal">日誌</Link>
          <Link to="/admin">管理</Link>
        </nav>
        <ModeControls />
      </header>
      <main>{children}</main>
      <MemberAuthModal />
    </div>
  );
}

export default Layout;
