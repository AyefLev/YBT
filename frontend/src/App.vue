<template>
  <router-view />
</template>

<style>
:root {
  --bg: #f6f8fb;
  --bg-elevated: #eef3f9;
  --surface: #ffffff;
  --surface-soft: #f8fafc;
  --surface-muted: #f1f5f9;
  --line: #e2e8f0;
  --line-strong: #cbd5e1;
  --text: #0f172a;
  --text-soft: #334155;
  --muted: #64748b;
  --muted-strong: #475569;
  --brand: #2563eb;
  --brand-dark: #1d4ed8;
  --brand-ink: #1e3a8a;
  --brand-soft: #eff6ff;
  --success: #047857;
  --success-soft: #ecfdf5;
  --warning: #b45309;
  --warning-soft: #fffbeb;
  --danger: #dc2626;
  --danger-soft: #fef2f2;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 12px 32px rgba(15, 23, 42, 0.06);
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --content-max: 1440px;
  color: var(--text);
  background: var(--bg);
  font-family:
    "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", ui-sans-serif,
    system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

html {
  min-width: 320px;
  background: var(--bg);
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  color: var(--text);
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.045), transparent 320px),
    var(--bg);
}

button,
input,
textarea,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

a {
  color: inherit;
}

::selection {
  color: #ffffff;
  background: var(--brand);
}

.page-shell {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.page-hero {
  display: flex;
  gap: 18px;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--line);
  padding-bottom: 18px;
}

.page-hero h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(1.75rem, 2.4vw, 2.35rem);
  font-weight: 850;
  letter-spacing: 0;
  line-height: 1.15;
}

.page-hero p {
  max-width: 860px;
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--brand-dark);
  font-size: 0.82rem;
  font-weight: 850;
}

.hero-actions,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.metric-grid,
.two-column-grid {
  display: grid;
  gap: 16px;
}

.metric-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.two-column-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel,
.metric-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.panel {
  padding: 18px;
}

.panel h2,
.panel h3 {
  margin: 0;
  color: var(--text);
  letter-spacing: 0;
}

.panel h2 {
  font-size: 1.08rem;
  line-height: 1.35;
}

.panel h3 {
  font-size: 1rem;
}

.panel-title {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.metric-card {
  display: grid;
  gap: 10px;
  min-height: 116px;
  padding: 18px;
}

.metric-card span,
.muted,
small {
  color: var(--muted);
}

.metric-card strong {
  color: var(--text);
  font-size: 2.1rem;
  font-weight: 850;
  line-height: 1;
}

.form-grid,
.stack,
.list {
  display: grid;
  gap: 14px;
}

.form-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.wide {
  grid-column: 1 / -1;
}

label {
  display: grid;
  gap: 7px;
  min-width: 0;
  color: var(--text-soft);
  font-size: 0.93rem;
  font-weight: 780;
}

input,
textarea,
select {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  color: var(--text);
  background: #ffffff;
  box-shadow: inset 0 1px 0 rgba(15, 23, 42, 0.02);
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    background 0.16s ease;
}

textarea {
  resize: vertical;
}

input::placeholder,
textarea::placeholder {
  color: #94a3b8;
}

input:focus,
textarea:focus,
select:focus {
  border-color: var(--brand);
  outline: none;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.checkbox {
  display: flex;
  gap: 9px;
  align-items: center;
}

.checkbox input {
  width: auto;
}

.btn-primary,
.btn-secondary,
.btn-danger,
button.btn-primary,
button.btn-secondary,
button.btn-danger {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 9px 14px;
  font-weight: 820;
  line-height: 1.2;
  text-decoration: none;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease,
    transform 0.08s ease,
    box-shadow 0.16s ease;
}

.btn-primary {
  color: #ffffff;
  background: var(--brand);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.16);
}

.btn-primary:hover {
  background: var(--brand-dark);
}

.btn-secondary {
  border-color: #dbeafe;
  color: var(--brand-ink);
  background: var(--brand-soft);
}

.btn-secondary:hover {
  border-color: #bfdbfe;
  background: #dbeafe;
}

.btn-danger {
  border-color: #fecaca;
  color: #991b1b;
  background: var(--danger-soft);
}

.btn-primary:active,
.btn-secondary:active,
.btn-danger:active {
  transform: translateY(1px);
}

button:disabled,
.btn-primary[aria-disabled="true"],
.btn-secondary[aria-disabled="true"] {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none;
}

.alert,
.notice {
  border-radius: var(--radius-md);
  padding: 11px 13px;
  line-height: 1.6;
}

.draft-banner {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #fed7aa;
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  color: #9a3412;
  background: #fff7ed;
  line-height: 1.6;
}

.alert {
  border: 1px solid #fecaca;
  color: #b42318;
  background: #fff1f2;
}

.notice {
  border: 1px solid #bfdbfe;
  color: var(--brand-ink);
  background: var(--brand-soft);
}

.status-pill {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  color: var(--brand-ink);
  background: var(--brand-soft);
  font-size: 0.8rem;
  font-weight: 820;
  line-height: 1.25;
}

.status-pill.success,
.status-pill.low,
.status-pill.approved {
  color: #166534;
  background: var(--success-soft);
}

.status-pill.warning,
.status-pill.medium,
.status-pill.pending_review {
  color: #92400e;
  background: var(--warning-soft);
}

.status-pill.danger,
.status-pill.high,
.status-pill.rejected {
  color: #991b1b;
  background: var(--danger-soft);
}

.empty-state {
  margin: 0;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-lg);
  padding: 18px;
  color: var(--muted);
  background: var(--surface-soft);
}

ul.clean-list {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

ul.clean-list > li {
  display: grid;
  gap: 7px;
  border-bottom: 1px solid #eef2f7;
  padding: 12px 0;
}

ul.clean-list > li:first-child {
  padding-top: 0;
}

ul.clean-list > li:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

@media (max-width: 900px) {
  .page-hero,
  .panel-title {
    display: grid;
  }

  .metric-grid,
  .two-column-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
