import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore, login as apiLogin, signup as apiSignup } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [spec, setSpec] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const refresh = useCallback(async () => {
    try { const me = await api("/api/me"); setUser(me); return me; }
    catch { tokenStore.clear(); setUser(null); return null; }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { api("/api/questionnaire").then(setSpec).catch(() => {}); if (tokenStore.get()) refresh(); }, [refresh]);

  const doLogin = async (email, pw) => { const { access_token } = await apiLogin(email, pw); tokenStore.set(access_token); return refresh(); };
  const doSignup = async (name, email, pw) => { const { access_token } = await apiSignup(name, email, pw); tokenStore.set(access_token); return refresh(); };
  const logout = () => { tokenStore.clear(); setUser(null); };

  return <Ctx.Provider value={{ user, spec, loading, refresh, login: doLogin, signup: doSignup, logout }}>{children}</Ctx.Provider>;
}
