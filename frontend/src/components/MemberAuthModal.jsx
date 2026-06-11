import { useState } from "react";
import { ACTIVITY_LEVEL_OPTIONS } from "../utils/bmr";
import { useAuth } from "../context/AuthContext";

const EMPTY_REGISTER_FORM = {
  account: "",
  password: "",
  name: "",
  gender: "male",
  heightCm: "",
  weightKg: "",
  age: "",
  activityLevel: "sedentary",
};

function MemberAuthModal() {
  const {
    authModalOpen,
    authModalMode,
    closeAuthModal,
    switchAuthMode,
    login,
    registerMember,
    authError,
    authSubmitting,
    demoMemberAccount,
    demoMemberPassword,
    demoWorkAccount,
    demoWorkPassword,
  } = useAuth();

  const [loginForm, setLoginForm] = useState({ account: "", password: "" });
  const [registerForm, setRegisterForm] = useState(EMPTY_REGISTER_FORM);

  if (!authModalOpen) {
    return null;
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    const result = await login(loginForm.account, loginForm.password);
    if (result.ok) {
      setLoginForm({ account: "", password: "" });
    }
  }

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    const result = await registerMember({
      ...registerForm,
      heightCm: Number(registerForm.heightCm),
      weightKg: Number(registerForm.weightKg),
      age: Number(registerForm.age),
    });

    if (result.ok) {
      setRegisterForm(EMPTY_REGISTER_FORM);
    }
  }

  return (
    <div className="modal-backdrop" onClick={closeAuthModal}>
      <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
        <div className="auth-modal-header">
          <div>
            <p className="eyebrow">會員模式</p>
            <h2>{authModalMode === "register" ? "註冊會員" : "會員登入"}</h2>
          </div>
          <button type="button" className="icon-button" onClick={closeAuthModal}>
            ×
          </button>
        </div>

        <div className="auth-tab-row">
          <button
            type="button"
            className={`auth-tab ${authModalMode === "login" ? "active" : ""}`}
            onClick={() => switchAuthMode("login")}
          >
            登入
          </button>
          <button
            type="button"
            className={`auth-tab ${authModalMode === "register" ? "active" : ""}`}
            onClick={() => switchAuthMode("register")}
          >
            註冊
          </button>
        </div>

        {authModalMode === "register" ? (
          <form className="auth-form" onSubmit={handleRegisterSubmit}>
            <label>
              <span>會員帳號</span>
              <input
                value={registerForm.account}
                onChange={(event) =>
                  setRegisterForm((current) => ({ ...current, account: event.target.value }))
                }
                placeholder="例如 user001"
              />
            </label>

            <label>
              <span>密碼</span>
              <input
                type="password"
                value={registerForm.password}
                onChange={(event) =>
                  setRegisterForm((current) => ({ ...current, password: event.target.value }))
                }
                placeholder="至少 4 碼"
              />
            </label>

            <label>
              <span>顯示名稱</span>
              <input
                value={registerForm.name}
                onChange={(event) =>
                  setRegisterForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="例如 小寬"
              />
            </label>

            <div className="auth-form-grid">
              <label>
                <span>性別</span>
                <select
                  value={registerForm.gender}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, gender: event.target.value }))
                  }
                >
                  <option value="male">男性</option>
                  <option value="female">女性</option>
                </select>
              </label>

              <label>
                <span>身高 (cm)</span>
                <input
                  type="number"
                  min="1"
                  value={registerForm.heightCm}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, heightCm: event.target.value }))
                  }
                  placeholder="170"
                />
              </label>

              <label>
                <span>體重 (kg)</span>
                <input
                  type="number"
                  min="1"
                  step="0.1"
                  value={registerForm.weightKg}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, weightKg: event.target.value }))
                  }
                  placeholder="65"
                />
              </label>

              <label>
                <span>年齡</span>
                <input
                  type="number"
                  min="1"
                  value={registerForm.age}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, age: event.target.value }))
                  }
                  placeholder="22"
                />
              </label>

              <label className="auth-form-wide">
                <span>活動量</span>
                <select
                  value={registerForm.activityLevel}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, activityLevel: event.target.value }))
                  }
                >
                  {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {authError ? <div className="error-text">{authError}</div> : null}

            <button type="submit" className="primary-button full-width" disabled={authSubmitting}>
              {authSubmitting ? "註冊中..." : "建立會員帳號"}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleLoginSubmit}>
            <p className="auth-helper-text">
              你也可以先用示範會員登入：
              <strong>{` ${demoMemberAccount} / ${demoMemberPassword}`}</strong>
            </p>
            <p className="auth-helper-text">
              <strong>{`管理員：${demoWorkAccount} / ${demoWorkPassword}`}</strong>
            </p>

            <label>
              <span>帳號</span>
              <input
                value={loginForm.account}
                onChange={(event) =>
                  setLoginForm((current) => ({ ...current, account: event.target.value }))
                }
                placeholder="請輸入會員帳號或管理員帳號"
              />
            </label>

            <label>
              <span>密碼</span>
              <input
                type="password"
                value={loginForm.password}
                onChange={(event) =>
                  setLoginForm((current) => ({ ...current, password: event.target.value }))
                }
                placeholder="請輸入密碼"
              />
            </label>

            {authError ? <div className="error-text">{authError}</div> : null}

            <button type="submit" className="primary-button full-width" disabled={authSubmitting}>
              {authSubmitting ? "登入中..." : "登入"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default MemberAuthModal;
