import { useState } from "react";
import { Mail, Lock, Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const MIN_PASSWORD = 8;

function Field({
  label,
  icon: Icon,
  type = "text",
  value,
  onChange,
  autoComplete,
  placeholder,
  trailing,
  disabled,
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-300 font-sans">{label}</span>
      <div className="mt-1.5 flex items-center gap-2.5 rounded-md bg-ink-950/80 border border-ink-800 px-3.5 py-2.5 transition-colors focus-within:border-accent-500/60 focus-within:bg-ink-950 focus-within:ring-1 focus-within:ring-accent-500/30">
        <Icon size={16} className="text-ink-500 shrink-0" />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          placeholder={placeholder}
          disabled={disabled}
          required
          className="flex-1 bg-transparent text-xs sm:text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none min-w-0"
        />
        {trailing}
      </div>
    </label>
  );
}

function PasswordField({ label, value, onChange, autoComplete, placeholder, disabled }) {
  const [visible, setVisible] = useState(false);
  return (
    <Field
      label={label}
      icon={Lock}
      type={visible ? "text" : "password"}
      value={value}
      onChange={onChange}
      autoComplete={autoComplete}
      placeholder={placeholder}
      disabled={disabled}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="text-ink-500 hover:text-ink-300 transition-colors"
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      }
    />
  );
}

function FormError({ message }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-rose-500/30 bg-rose-950/20 px-3.5 py-2.5"
    >
      <AlertCircle size={15} className="text-rose-400 shrink-0 mt-0.5" />
      <p className="text-xs text-rose-200 leading-relaxed font-sans">{message}</p>
    </div>
  );
}

function SubmitButton({ loading, children }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-xs sm:text-sm font-medium bg-accent-600 text-white hover:bg-accent-500 transition-all active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
    >
      {loading && <Loader2 size={15} className="animate-spin" />}
      {children}
    </button>
  );
}

export function LoginForm({ onSuccess, onSwitch }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim(), password);
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4" noValidate={false}>
      <Field
        label="Email address"
        icon={Mail}
        type="email"
        value={email}
        onChange={setEmail}
        autoComplete="email"
        placeholder="you@example.com"
        disabled={loading}
      />
      <PasswordField
        label="Password"
        value={password}
        onChange={setPassword}
        autoComplete="current-password"
        placeholder="Your password"
        disabled={loading}
      />
      <FormError message={error} />
      <SubmitButton loading={loading}>{loading ? "Signing in..." : "Log in"}</SubmitButton>
      <p className="text-center text-xs text-ink-400">
        Don&apos;t have an account?{" "}
        <button
          type="button"
          onClick={onSwitch}
          className="text-accent-400 hover:text-accent-300 font-medium underline underline-offset-2"
        >
          Create one
        </button>
      </p>
    </form>
  );
}

export function RegisterForm({ onSuccess, onSwitch }) {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters long.`);
      return;
    }
    if (password !== confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setLoading(true);
    try {
      await register(email.trim(), password);
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field
        label="Email address"
        icon={Mail}
        type="email"
        value={email}
        onChange={setEmail}
        autoComplete="email"
        placeholder="you@example.com"
        disabled={loading}
      />
      <PasswordField
        label="Password"
        value={password}
        onChange={setPassword}
        autoComplete="new-password"
        placeholder={`At least ${MIN_PASSWORD} characters`}
        disabled={loading}
      />
      <PasswordField
        label="Confirm password"
        value={confirm}
        onChange={setConfirm}
        autoComplete="new-password"
        placeholder="Re-enter your password"
        disabled={loading}
      />
      <FormError message={error} />
      <SubmitButton loading={loading}>
        {loading ? "Creating account..." : "Create Account"}
      </SubmitButton>
      <p className="text-center text-xs text-ink-400">
        Already have an account?{" "}
        <button
          type="button"
          onClick={onSwitch}
          className="text-accent-400 hover:text-accent-300 font-medium underline underline-offset-2"
        >
          Log in
        </button>
      </p>
    </form>
  );
}
