<template>
  <router-view />
</template>

<style>
:root {
  --bg: #f4f7fb;
  --surface: #ffffff;
  --surface-soft: #f8fafc;
  --line: #dbe4f0;
  --line-strong: #c7d2e3;
  --text: #122033;
  --muted: #64748b;
  --brand: #2563eb;
  --brand-dark: #1746a2;
  --brand-soft: #eaf2ff;
  --success: #047857;
  --success-soft: #dcfce7;
  --warning: #b45309;
  --warning-soft: #fef3c7;
  --danger: #dc2626;
  --danger-soft: #fee2e2;
  color: var(--text);
  background: var(--bg);
  font-family:
    "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", Inter, ui-sans-serif,
    system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

html {
  background: var(--bg);
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  background: var(--bg);
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

.page-shell {
  display: grid;
  gap: 20px;
}

.page-hero {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.page-hero h1 {
  margin: 0;
  color: var(--text);
  font-size: 2rem;
  line-height: 1.2;
}

.page-hero p {
  max-width: 780px;
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--brand);
  font-size: 0.9rem;
  font-weight: 800;
}

.hero-actions,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
  border-radius: 8px;
  background: var(--surface);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
}

.panel {
  padding: 18px;
}

.panel h2,
.panel h3 {
  margin: 0;
  color: var(--text);
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
  padding: 18px;
}

.metric-card span,
.muted,
small {
  color: var(--muted);
}

.metric-card strong {
  color: var(--text);
  font-size: 2rem;
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
  color: #334155;
  font-weight: 800;
}

input,
textarea,
select {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  padding: 10px 11px;
  color: var(--text);
  background: #ffffff;
}

textarea {
  resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
  border-color: var(--brand);
  outline: 3px solid rgba(37, 99, 235, 0.16);
}

.checkbox {
  display: flex;
  gap: 8px;
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
  border: 0;
  border-radius: 6px;
  padding: 10px 14px;
  font-weight: 800;
  text-decoration: none;
}

.btn-primary {
  color: #ffffff;
  background: var(--brand);
}

.btn-primary:hover {
  background: var(--brand-dark);
}

.btn-secondary {
  color: var(--brand-dark);
  background: var(--brand-soft);
}

.btn-danger {
  color: #991b1b;
  background: var(--danger-soft);
}

button:disabled,
.btn-primary[aria-disabled="true"],
.btn-secondary[aria-disabled="true"] {
  cursor: not-allowed;
  opacity: 0.62;
}

.alert,
.notice {
  border-radius: 6px;
  padding: 10px 12px;
  line-height: 1.6;
}

.draft-banner {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  padding: 10px 12px;
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
  color: #1e3a8a;
  background: #eff6ff;
}

.status-pill {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  color: var(--brand-dark);
  background: var(--brand-soft);
  font-size: 0.82rem;
  font-weight: 800;
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
  border-radius: 8px;
  padding: 16px;
  color: var(--muted);
  background: var(--surface-soft);
}

ul.clean-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

ul.clean-list > li {
  display: grid;
  gap: 6px;
  border-bottom: 1px solid #edf1f7;
  padding-bottom: 12px;
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
