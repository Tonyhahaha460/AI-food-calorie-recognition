import { Link } from "react-router-dom";
import MemberAuthModal from "./MemberAuthModal";
import ModeControls from "./ModeControls";

function Layout({ children }) {
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link to="/" className="brand-mark">
          AI Food Quest
        </Link>
        <nav className="site-nav">
          <Link to="/">主城</Link>
          <Link to="/recognition">掃描任務</Link>
          <Link to="/journal">冒險日誌</Link>
          <Link to="/admin">資料工坊</Link>
        </nav>
        <ModeControls />
      </header>
      <main>{children}</main>
      <MemberAuthModal />
    </div>
  );
}

export default Layout;
