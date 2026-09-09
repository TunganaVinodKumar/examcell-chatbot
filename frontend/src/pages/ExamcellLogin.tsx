import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import Header from "@/components/Header";

const API_BASE =
  import.meta.env.VITE_API_BASE || "https://examcell-chatbot.onrender.com";

const ExamcellLogin = () => {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setError("Please fill all fields");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/examcell/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: trimmedEmail,
          password,
        }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Login request failed");
      }

      if (data?.success) {
        localStorage.setItem("examcellLoggedIn", "true");
        navigate("/examcell-dashboard");
        return;
      }

      setError(data?.message || "Invalid credentials");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Server error. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <Header />

      <main className="flex min-h-[calc(100vh-88px)] items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="rounded-[28px] border border-slate-200 bg-white p-8 shadow-[0_18px_50px_rgba(15,23,42,0.12)] md:p-10">
            <div className="mb-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800">
                <ShieldCheck className="h-8 w-8 text-amber-300" />
              </div>

              <h1 className="font-display text-3xl font-bold text-primary">
                Exam Cell Login
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Sign in to access the exam cell dashboard
              </p>
            </div>

            <form
              autoComplete="off"
              className="flex flex-col gap-5"
              onSubmit={(e) => {
                e.preventDefault();
                handleLogin();
              }}
            >
              <input
                type="text"
                name="fake-username"
                autoComplete="username"
                style={{ display: "none" }}
              />
              <input
                type="password"
                name="fake-password"
                autoComplete="new-password"
                style={{ display: "none" }}
              />

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">
                  Exam Cell ID
                </label>
                <input
                  type="text"
                  autoComplete="off"
                  name="examcell-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your Exam Cell ID"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-foreground outline-none transition focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">
                  Password
                </label>
                <input
                  type="password"
                  autoComplete="off"
                  name="examcell-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-foreground outline-none transition focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/20"
                />
              </div>

              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-center text-sm text-red-600">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-1 w-full rounded-xl bg-primary py-3 font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Logging in..." : "Login"}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ExamcellLogin;
