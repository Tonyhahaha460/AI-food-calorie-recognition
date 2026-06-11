import { useAuth } from "../context/AuthContext";

function ModeControls() {
  const {
    isMemberLoggedIn,
    memberName,
    openAuthModal,
    logoutMember,
    isWorkMode,
    workAccountName,
    logoutWork,
    authReady,
  } = useAuth();

  const loggedLabel = isWorkMode
    ? `管理員：${workAccountName || "admin"}`
    : isMemberLoggedIn
      ? `會員：${memberName || "member"}`
      : "訪客";

  return (
    <div className="mode-controls">
      <div className="auth-group">
        <span className={`mode-chip ${isWorkMode ? "work" : isMemberLoggedIn ? "member" : "visitor"}`}>
          {authReady ? loggedLabel : "登入狀態讀取中..."}
        </span>

        {isWorkMode ? (
          <button type="button" className="secondary-button small-button" onClick={logoutWork}>
            管理員登出
          </button>
        ) : isMemberLoggedIn ? (
          <button type="button" className="secondary-button small-button" onClick={logoutMember}>
            會員登出
          </button>
        ) : (
          <>
            <button type="button" className="secondary-button small-button" onClick={() => openAuthModal("login")}>
              會員登入
            </button>
            <button type="button" className="primary-button small-button" onClick={() => openAuthModal("register")}>
              註冊會員
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default ModeControls;
