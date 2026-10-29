import { announceAuthChange } from "../serverWorkspace";
import { useEffect, useState } from "react";
import { LogIn, LogOut, UserPlus, ShieldCheck } from "lucide-react";
import { accountRequest, ApiError, type Account } from "../api";
import { PageTitle } from "../components/ui";

export function AccountPage() {
  const [account, setAccount] = useState<Account | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const changed=()=>setRetry(n=>n+1);
    const storage=(e:StorageEvent)=>{if(e.key==="study-with-ai:auth-change") changed();};
    window.addEventListener("study-auth-changed",changed);
    window.addEventListener("storage",storage);
    return ()=>{window.removeEventListener("study-auth-changed",changed);window.removeEventListener("storage",storage);};
  },[]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    accountRequest<Account>("/auth/me", undefined, controller.signal)
      .then(setAccount)
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setAccount(null);
        if (!(e instanceof ApiError && e.status === 401))
          setError(e instanceof Error ? e.message : "无法读取账号");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [retry]);
  return (
    <>
      <PageTitle
        eyebrow="YOUR ACCOUNT"
        title="账号与登录"
        description="创建自己的账号，开始建立独立的学习空间。"
      />
      <div className="account-layout">
        <section className="panel account-panel">
          {loading ? (
            <p role="status">正在检查登录状态…</p>
          ) : account ? (
            <>
              <span className="account-symbol">
                <ShieldCheck size={32} />
              </span>
              <h2>你好，{account.username}</h2>
              <p className="muted">你已登录，账号已保存。</p>
              <dl className="account-facts">
                <div>
                  <dt>用户名</dt>
                  <dd>{account.username}</dd>
                </div>
                <div>
                  <dt>注册时间</dt>
                  <dd>{new Date(account.created_at).toLocaleString()}</dd>
                </div>
              </dl>
              <button
                className="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await accountRequest("/auth/logout", {});
                    announceAuthChange();
                    setAccount(null);
                    setPassword("");
                    setConfirm("");
                    setNotice("已退出登录。");
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "退出失败，请重试",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <LogOut size={18} />
                {busy ? "正在退出…" : "退出登录"}
              </button>
            </>
          ) : (
            <>
              <div className="tab-row" role="group" aria-label="账号操作">
                <button
                  disabled={busy}
                  className={mode === "login" ? "selected" : ""}
                  onClick={() => {
                    setMode("login");
                    setError("");
                    setNotice("");
                    setPassword("");
                    setConfirm("");
                  }}
                >
                  登录
                </button>
                <button
                  disabled={busy}
                  className={mode === "register" ? "selected" : ""}
                  onClick={() => {
                    setMode("register");
                    setError("");
                    setNotice("");
                    setPassword("");
                    setConfirm("");
                  }}
                >
                  注册
                </button>
              </div>
              <form
                onSubmit={async (event) => {
                  event.preventDefault();
                  setError("");
                  setNotice("");
                  if (mode === "register" && password !== confirm) {
                    setError("两次输入的密码不一致。");
                    return;
                  }
                  setBusy(true);
                  try {
                    const user = await accountRequest<Account>(
                      `/auth/${mode}`,
                      { username, password },
                    );
                    if (mode === "login") {
                      setAccount(user);
                      announceAuthChange();
                      setNotice("");
                    } else {
                      setMode("login");
                      setUsername(user.username);
                      setNotice("注册成功，请登录。个人目录已创建。");
                    }
                    setPassword("");
                    setConfirm("");
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "操作失败，请重试。",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <label className="field">
                  用户名
                  <input
                    required
                    minLength={3}
                    maxLength={64}
                    autoComplete="username"
                    disabled={busy}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="3–64 个字符，支持中文"
                  />
                </label>
                <label className="field">
                  密码
                  <input
                    required
                    type="password"
                    minLength={8}
                    maxLength={128}
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    disabled={busy}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="8–128 个字符"
                  />
                </label>
                {mode === "register" && (
                  <label className="field">
                    确认密码
                    <input
                      required
                      type="password"
                      minLength={8}
                      maxLength={128}
                      autoComplete="new-password"
                      disabled={busy}
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                    />
                  </label>
                )}
                <button className="button primary" disabled={busy}>
                  {mode === "login" ? (
                    <LogIn size={18} />
                  ) : (
                    <UserPlus size={18} />
                  )}
                  {busy
                    ? "正在处理…"
                    : mode === "login"
                      ? "登录账号"
                      : "创建账号"}
                </button>
              </form>
            </>
          )}
          {error && (
            <div className="account-error" role="alert">
              {error}
              <button
                className="text-link"
                disabled={busy || loading}
                onClick={() => setRetry((n) => n + 1)}
              >
                重新检查连接
              </button>
            </div>
          )}
          {notice && (
            <p className="account-notice" role="status">
              {notice}
            </p>
          )}
        </section>
        <aside className="panel account-explanation">
          <h2>账号功能已接入</h2>
          <p>现在可以注册、登录和退出账号。刷新页面后会重新确认登录状态。</p>
          <h3>课程已接入个人空间</h3>
          <p>
            登录后，“我的课程”显示你的个人课程。课程与章节会保存到服务器；顶部可以切换本地演示，原有示例不会自动导入账号。练习、作业、作答记录与课程资料也会保存；开放练习与作业文字答案支持 AI 批改；配置个人模型后可使用教师与助教，附件仍待评阅。
          </p>
          <a className="text-link" href="#/">
            进入我的课程 →
          </a>
        </aside>
      </div>
    </>
  );
}
