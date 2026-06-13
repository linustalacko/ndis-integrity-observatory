// Thin typed client for the NDIS Integrity API.
// Same-origin in production (empty BASE -> relative /api); localhost in dev.
const BASE = import.meta.env.VITE_API ?? '';

async function get<T>(path: string): Promise<T> {
	const r = await fetch(`${BASE}${path}`);
	if (!r.ok) throw new Error(`${r.status} ${path}`);
	return r.json();
}

export const api = {
	overview: () => get<Overview>('/api/overview'),
	register: (q: string) => get<{ count: number; actions: Action[] }>(`/api/register?q=${encodeURIComponent(q)}`),
	phoenix: (tier: string) => get<PhoenixResp>(`/api/phoenix?tier=${tier}`),
	check: (q: string) => get<CheckResp>(`/api/check?q=${encodeURIComponent(q)}`),
	dossierList: () => get<{ leads: { name: string; confidence: number }[] }>('/api/dossier-list'),
	dossier: (name: string) => get<{ markdown: string }>(`/api/dossier?name=${encodeURIComponent(name)}`),
	typologies: () => get<TypologyResp>('/api/typologies'),
	typologySamples: (t: string) => get<{ samples: Sample[] }>(`/api/typology-samples?typology=${encodeURIComponent(t)}`),
	snapshots: () => get<{ snapshots: string[] }>('/api/snapshots'),
	diff: (a: string, b: string) => get<DiffResp>(`/api/diff?a=${a}&b=${b}`),
	money: () => get<MoneyResp>('/api/money'),
	signals: () => get<SignalsResp>('/api/signals'),
	claimsDemo: () => get<ClaimsResp>('/api/claims-demo'),
	claimsUpload: async (file: File) => {
		const fd = new FormData();
		fd.append('file', file);
		const r = await fetch(`${BASE}/api/claims`, { method: 'POST', body: fd });
		return r.json() as Promise<ClaimsResp>;
	},
	claimsImage: async (file: File) => {
		const fd = new FormData();
		fd.append('file', file);
		const r = await fetch(`${BASE}/api/claims-image`, { method: 'POST', body: fd });
		return r.json() as Promise<ClaimsResp>;
	},
	report: async (source: string, invoices: any[]) => {
		const r = await fetch(`${BASE}/api/report`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ source, invoices })
		});
		return r.json() as Promise<{ submitted: number; providers?: string[]; message?: string }>;
	},
	registry: () => get<RegistryResp>('/api/registry')
};

export type Report = {
	report_id: string; created_at: string; provider_name: string; provider_abn: string;
	state: string; postcode: string; city: string; services: string;
	billed: number; at_risk: number; n_breaches: number; rules: string[];
	findings: { line: number; rule: string; detail: string; at_risk: number }[];
	source: string; already_sanctioned: string;
};
export type RegistryResp = {
	reports: Report[]; total_at_risk: number; count: number;
	providers: number; sanctioned: number;
};

export type Totals = {
	actions: number; banning_orders: number; compliance_notices: number;
	revocations: number; phoenix_high: number;
};
export type Overview = {
	totals: Totals;
	snapshots: { from: string; to: string; count: number };
	by_type: Record<string, number>;
	monthly: { month: string; type: string; n: number }[];
	by_state: { state: string; n: number }[];
	hotspots: { location: string; n: number }[];
};
export type Action = {
	action_id: string; type: string; name: string; abn: string; city: string;
	state: string; postcode: string; date_from: string; date_to: string;
	first_seen: string; last_seen: string; detail: string;
};
export type Lead = {
	confidence: number; tier: string; name: string; type: string;
	sanction_date: string; act_state: string; abn: string; namesakes: number;
	geo: string; match_type: string; note: string;
};
export type PhoenixResp = { counts: Record<string, number>; leads: Lead[] };
export type CheckResp = {
	query: string; verdict: string; risk: string;
	sanctions: Action[]; compliance_notices: Action[];
	phoenix_links: any[]; disclaimer: string;
};
export type TypologyResp = {
	classified: number; verified: number;
	distribution: { typology: string; n: number }[];
};
export type Sample = { name: string; type: string; date_from: string; quote: string };
export type DiffResp = {
	new: { type: string; name: string; state: string; date_from: string }[];
	gone: { type: string; name: string; state: string; date_from: string; last_seen: string }[];
};
export type MoneyCase = { date: string; amount: number; title: string; kind: string; url: string };
export type MoneyResp = {
	systemic: { label: string; low: number; high: number; basis: string; source: string };
	cases: MoneyCase[];
	case_total: number;
	by_kind: Record<string, number>;
	case_count: number;
};
export type Region = {
	state: string; district: string; providers_first: number; providers_last: number;
	growth: number; excess_growth: number; frag: number | null;
	spend_per_provider: number | null; enf_density: number; risk: number;
};
export type Operator = {
	name: string; type: string; date_from: string; state: string; postcode: string;
	n_abns: number; n_post_ban: number; abns: string[]; sanctioned: boolean;
};
export type Family = {
	surname: string; postcode: string; state: string; people: string[];
	n_people: number; n_sanctioned: number;
	members: { name: string; type: string; date_from: string }[];
};
export type SignalsResp = {
	regions: Region[]; national_growth: number;
	national_series: { c: number; quarter: string }[];
	operators: Operator[]; families: Family[];
};
export type Finding = {
	line: number; rule: string; severity: string; detail: string;
	citation: string; at_risk: number; provider: string;
};
export type ProviderRisk = { provider: string; findings: number; at_risk: number; rules: string[] };
export type ClaimsResp = {
	lines: number; breaches: number; warnings: number; at_risk: number; billed: number;
	providers: ProviderRisk[]; findings: Finding[]; invoices: Record<string, string>[];
};
