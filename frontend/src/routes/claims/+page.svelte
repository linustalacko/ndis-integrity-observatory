<script lang="ts">
	import { api, type ClaimsResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	const BASE = import.meta.env.VITE_API ?? 'http://localhost:8000';
	let data = $state<ClaimsResp | null>(null);
	let filename = $state('demo batch (326 lines)');
	let busy = $state(false);

	$effect(() => {
		api.claimsDemo().then((d) => (data = d));
	});
	async function onUpload(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		busy = true;
		filename = file.name;
		try {
			data = await api.claimsUpload(file);
		} finally {
			busy = false;
		}
	}
	function money(n: number) {
		if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
		if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
		return `$${n.toFixed(0)}`;
	}
	const pct = $derived(data && data.billed ? (data.at_risk / data.billed) * 100 : 0);
</script>

<Header
	title="Claims lab"
	lede="Screen an invoice book against the price caps, the fraud rules, and the live register. This is where new fraud is caught — point it at real claims data."
/>

<div class="bar-actions">
	<button class:active={filename.startsWith('demo')} onclick={() => { filename = 'demo batch (326 lines)'; api.claimsDemo().then((d) => (data = d)); }}>
		Demo batch
	</button>
	<label class="upload">
		Upload CSV
		<input type="file" accept=".csv" onchange={onUpload} />
	</label>
	<a class="tmpl" href={`${BASE}/api/claims-template`}>Template</a>
	<span class="fname muted">{busy ? 'screening…' : filename}</span>
</div>

{#if data}
	<section class="metrics">
		<div class="metric"><span class="v num">{data.lines}</span><span class="k">Lines screened</span></div>
		<div class="metric"><span class="v num">{money(data.billed)}</span><span class="k">Total billed</span></div>
		<div class="metric flag"><span class="v num">{money(data.at_risk)}</span><span class="k">Flagged at risk</span></div>
		<div class="metric"><span class="v num">{pct.toFixed(1)}%</span><span class="k">Of billings</span></div>
		<div class="metric"><span class="v num">{data.breaches}</span><span class="k">Breaches</span></div>
	</section>

	<section class="block">
		<h2>Providers by exposure</h2>
		<table>
			<thead><tr><th>Provider</th><th>Findings</th><th>Rules</th><th class="r">At risk</th></tr></thead>
			<tbody>
				{#each data.providers as p}
					<tr>
						<td><strong>{p.provider}</strong></td>
						<td class="num">{p.findings}</td>
						<td>{#each p.rules as r}<span class="tag">{r}</span>{/each}</td>
						<td class="num r amt">{money(p.at_risk)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section class="block">
		<h2>Findings <span class="muted num">({data.findings.length})</span></h2>
		<table>
			<thead><tr><th>Line</th><th>Rule</th><th></th><th>Detail</th><th class="r">At risk</th></tr></thead>
			<tbody>
				{#each data.findings as f}
					<tr>
						<td class="num">{f.line}</td>
						<td><strong>{f.rule}</strong></td>
						<td><span class="dot {f.severity === 'breach' ? 'critical' : 'elevated'}"></span></td>
						<td class="dcell">{f.detail}</td>
						<td class="num r">{f.at_risk ? money(f.at_risk) : '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>
{/if}

<style>
	.bar-actions {
		display: flex;
		gap: 8px;
		align-items: center;
		margin-bottom: 30px;
	}
	.upload,
	.tmpl {
		font-size: 13px;
		border: 1px solid var(--line-2);
		padding: 9px 16px;
		cursor: pointer;
		color: var(--ink);
	}
	.upload:hover,
	.tmpl:hover {
		background: var(--hover);
		border-color: var(--ink);
		text-decoration: none;
	}
	.upload input {
		display: none;
	}
	.fname {
		font-size: 12px;
		margin-left: 6px;
	}
	.metrics {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 26px;
		padding: 26px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
		margin-bottom: 40px;
	}
	.metric.flag .v {
		color: var(--critical);
	}
	.block {
		margin-top: 44px;
	}
	.block h2 {
		margin-bottom: 16px;
	}
	.r {
		text-align: right;
	}
	.amt {
		font-weight: 600;
	}
	.dcell {
		max-width: 560px;
	}
	.tag {
		margin-right: 4px;
	}
	@media (max-width: 900px) {
		.metrics {
			grid-template-columns: repeat(2, 1fr);
			gap: 20px;
		}
	}
</style>
