import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  loginRequest,
  registerRequest,
  updateCurrentUser,
} from "../api/authApi";
import {
  clearStoredAuthSession,
  loadStoredAuthSession,
  saveStoredAuthSession,
} from "../utils/authSession";

const VALID_GENDERS = ["male", "female"];
const VALID_ACTIVITY_LEVELS = ["sedentary", "light", "moderate", "active", "very_active"];

const EMPTY_USER = {
  account: "",
  name: "",
  role: "visitor",
  gender: "male",
  heightCm: 0,
  weightKg: 0,
  age: 0,
  activityLevel: "sedentary",
};

const DEMO_MEMBER = {
  account: "member",
  password: "1234",
  name: "示範會員",
};

const DEMO_ADMIN = {
  account: "admin",
  password: "1234",
  name: "示範管理員",
};

const AuthContext = createContext(null);

function normalizeUser(user = {}) {
  const role = String(user.role || "").trim().toLowerCase() || "visitor";
  const gender = VALID_GENDERS.includes(String(user.gender || "").trim())
    ? String(user.gender).trim()
    : "male";
  const activityLevel = VALID_ACTIVITY_LEVELS.includes(String(user.activityLevel || "").trim())
    ? String(user.activityLevel).trim()
    : "sedentary";

  return {
    account: String(user.account || "").trim().toLowerCase(),
    name: String(user.name || "").trim(),
    role,
    gender,
    heightCm: Number(user.heightCm || 0),
    weightKg: Number(user.weightKg || 0),
    age: Number(user.age || 0),
    activityLevel,
  };
}

function buildSession(token, user) {
  return {
    token: String(token || "").trim(),
    user: normalizeUser(user),
  };
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState("login");

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const stored = loadStoredAuthSession();
      if (!stored?.token) {
        if (!cancelled) {
          setAuthReady(true);
        }
        return;
      }

      try {
        const response = await fetchCurrentUser(stored.token);
        if (cancelled) {
          return;
        }
        const nextSession = buildSession(stored.token, response.user);
        saveStoredAuthSession(nextSession);
        setSession(nextSession);
      } catch {
        clearStoredAuthSession();
        if (!cancelled) {
          setSession(null);
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  function openAuthModal(mode = "login") {
    setAuthError("");
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  }

  function closeAuthModal() {
    setAuthError("");
    setAuthModalOpen(false);
  }

  function switchAuthMode(mode) {
    setAuthError("");
    setAuthModalMode(mode);
  }

  async function login(account, password) {
    setAuthSubmitting(true);
    setAuthError("");

    try {
      const result = await loginRequest(account, password);
      const nextSession = buildSession(result.token, result.user);
      saveStoredAuthSession(nextSession);
      setSession(nextSession);
      closeAuthModal();
      return { ok: true, role: nextSession.user.role };
    } catch (error) {
      const message = error instanceof Error ? error.message : "登入失敗。";
      setAuthError(message);
      return { ok: false, role: "" };
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function registerMember(form = {}) {
    setAuthSubmitting(true);
    setAuthError("");

    try {
      const result = await registerRequest(form);
      const nextSession = buildSession(result.token, result.user);
      saveStoredAuthSession(nextSession);
      setSession(nextSession);
      closeAuthModal();
      return { ok: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : "註冊失敗。";
      setAuthError(message);
      return { ok: false };
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function updateMemberProfile(updates = {}) {
    if (!session?.token) {
      return { ok: false };
    }

    try {
      const result = await updateCurrentUser(session.token, updates);
      const nextSession = buildSession(session.token, result.user);
      saveStoredAuthSession(nextSession);
      setSession(nextSession);
      return { ok: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : "更新會員資料失敗。";
      setAuthError(message);
      return { ok: false, error: message };
    }
  }

  function clearSession() {
    clearStoredAuthSession();
    setSession(null);
    setAuthError("");
  }

  function logoutMember() {
    clearSession();
  }

  function logoutWork() {
    clearSession();
  }

  const user = session?.user || EMPTY_USER;
  const isMemberLoggedIn = user.role === "member";
  const isWorkMode = user.role === "admin";

  const value = useMemo(
    () => ({
      member: isMemberLoggedIn ? user : { ...EMPTY_USER },
      isMemberLoggedIn,
      memberName: isMemberLoggedIn ? user.name : "",
      memberAccount: isMemberLoggedIn ? user.account : "",
      memberProfile: {
        gender: user.gender,
        heightCm: user.heightCm,
        weightKg: user.weightKg,
        age: user.age,
        activityLevel: user.activityLevel,
      },
      login,
      registerMember,
      updateMemberProfile,
      logoutMember,
      authError,
      authReady,
      authSubmitting,
      authModalOpen,
      authModalMode,
      openAuthModal,
      closeAuthModal,
      switchAuthMode,
      workMode: isWorkMode ? "work" : "visitor",
      isWorkMode,
      workAccountName: isWorkMode ? user.name : "",
      workAccount: isWorkMode ? user.account : "",
      logoutWork,
      currentUser: user,
      authToken: session?.token || "",
      demoMemberAccount: DEMO_MEMBER.account,
      demoMemberPassword: DEMO_MEMBER.password,
      demoMemberName: DEMO_MEMBER.name,
      demoWorkAccount: DEMO_ADMIN.account,
      demoWorkPassword: DEMO_ADMIN.password,
      demoWorkName: DEMO_ADMIN.name,
    }),
    [
      authError,
      authModalMode,
      authModalOpen,
      authReady,
      authSubmitting,
      isMemberLoggedIn,
      isWorkMode,
      session?.token,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
