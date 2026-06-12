<script lang="ts">
	import { api, type ClaimsResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let data = $state<ClaimsResp | null>(null);
	let mode = $state<'demo' | 'upload'>('demo');

	$effect(() => {
		api.claimsDemo().then((d) => (data = d));
	});
	async function onUpload(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		mode = 'upload';
		data = await api.claimsUpload(file);
	}
	function sev(s: string) {
		return s === 'breach' ? 'critical' : 'elevated';
	}
	const cols = $derived(data?.invoices.length ? Object.keys(data.invoices[0]) : []);
</script>

<Header
	kicker="Invoice screening against the rules"
	title="Claims lab"
	lede="Deterministic screening against the NDIS Support Catalogue 2025-26 price caps, the NDIA's own fraud typologies, and the live enforcement register. The demo batch seeds every detectable fraud type; upload a CSV to screen your own."
/>

<div class="bar-actions">
	<button class:active={mode === 'demo'} onclick={() => { mode = 'demo'; api.claimsDemo().then((d) => (data = d)); }}>
		Demo batch
	</button>
	<label class="upload">
		Upload CSV
		<input type="file" accept=".csv" onchange={onUpload} />
	</label>
</div>

{#if data}
	<section class="metrics">
		<div class="metric"><span class="v num">{data.lines}</span><span class="k">Invoice lines</span></div>
		<div class="metric"><span class="v num">{data.breaches}</span><span class="k"><span class="dot critical"></span> Breaches</span></div>
		<div class="metric"><span class="v num">{data.warnings}</span><span class="k"><span class="dot elevated"></span> Warnings</span></div>
	</section>

	<h2>Findings</h2>
	<table>
		<thead><tr><th>Line</th><th>Rule</th><th></th><th>Detail</th><th>Citation</th></tr></thead>
		<tbody>
			{#each data.findings as f}
				<tr>
					<td class="num">{f.line}</td>
					<td><strong>{f.rule}</strong></td>
					<td><span class="dot {sev(f.severity)}"></span></td>
					<td>{f.detail}</td>
					<td class="muted">{f.citation}</td>
				</tr>
			{/each}
		</tbody>
	</table>

	<h2 class="sub">Invoice batch</h2>
	<div class="scroll">
		<table class="mono-table">
			<thead><tr>{#each cols as c}<th>{c}</th>{/each}</tr></thead>
			<tbody>
				{#each data.invoices as row}
					<tr>{#each cols as c}<td class="mono">{row[c]}</td>{/each}</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.bar-actions {
		display: flex;
		gap: 8px;
		margin-bottom: 30px;
	}
	.upload {
		font-size: 13px;
		border: 1px solid var(--line-2);
		padding: 9px 16px;
		cursor: pointer;
	}
	.upload:hover {
		background: var(--hover);
		border-color: var(--ink);
	}
	.upload input {
		display: none;
	}
	.metrics {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 28px;
		padding: 26px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
		max-width: 560px;
		margin-bottom: 36px;
	}
	.metric .k {
		display: flex;
		align-items: center;
		gap: 7px;
	}
	h2 {
		margin-bottom: 16px;
	}
	h2.sub {
		margin-top: 44px;
	}
	.scroll {
		overflow-x: auto;
		border: 1px solid var(--line);
	}
	.mono-table th,
	.mono-table td {
		white-space: nowrap;
		font-size: 11.5px;
		padding: 7px 10px;
	}
</style>
