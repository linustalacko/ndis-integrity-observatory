<script lang="ts">
	import { api, type ClaimsResp } from '$lib/api';
	import { money } from '$lib/format';
	import Header from '$lib/Header.svelte';

	const BASE = import.meta.env.VITE_API ?? '';
	let data = $state<ClaimsResp | null>(null);
	let status = $state<'idle' | 'screening' | 'done'>('idle');
	let source = $state('csv');
	let submitted = $state<{ submitted: number; providers?: string[]; message?: string } | null>(null);
	let dragging = $state(false);

	async function handle(file: File) {
		submitted = null;
		status = 'screening';
		const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif)$/i.test(file.name);
		source = isImage ? 'image' : 'csv';
		data = isImage ? await api.claimsImage(file) : await api.claimsUpload(file);
		status = 'done';
	}
	function onPick(e: Event) {
		const f = (e.target as HTMLInputElement).files?.[0];
		if (f) handle(f);
	}
	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const f = e.dataTransfer?.files?.[0];
		if (f) handle(f);
	}
	async function demo() {
		submitted = null;
		status = 'screening';
		source = 'csv';
		data = await api.claimsDemo();
		status = 'done';
	}
	async function reportFraud() {
		if (!data) return;
		submitted = await api.report(source, data.invoices);
	}
	const hasFraud = $derived(!!data && data.breaches > 0);
</script>

<Header
	title="Report fraud"
	lede="Drop an invoice CSV or a photo of an invoice. If the rules flag fraud, send it to the shared registry with one tap."
/>

<div
	class="drop"
	class:dragging
	role="button"
	tabindex="0"
	ondragover={(e) => {
		e.preventDefault();
		dragging = true;
	}}
	ondragleave={() => (dragging = false)}
	ondrop={onDrop}
>
	<p class="big">Drop a CSV or invoice image here</p>
	<p class="muted">or</p>
	<div class="picks">
		<label class="btn">Choose file<input type="file" accept=".csv,image/*" onchange={onPick} /></label>
		<button onclick={demo}>Try the demo batch</button>
		<a class="link" href={`${BASE}/api/claims-template`}>CSV template</a>
	</div>
</div>

{#if status === 'screening'}
	<p class="muted screening">Screening…</p>
{:else if status === 'done' && data}
	<section class="result">
		<div class="metrics">
			<div class="metric"><span class="v num">{data.lines}</span><span class="k">Lines</span></div>
			<div class="metric"><span class="v num">{money(data.billed)}</span><span class="k">Billed</span></div>
			<div class="metric flag"><span class="v num">{money(data.at_risk)}</span><span class="k">At risk</span></div>
			<div class="metric"><span class="v num">{data.breaches}</span><span class="k">Breaches</span></div>
		</div>

		{#if hasFraud}
			{#if submitted}
				{#if submitted.submitted > 0}
					<div class="reported ok">
						✓ Reported {submitted.submitted} provider{submitted.submitted === 1 ? '' : 's'} to the
						registry — <a href="/registry">view the registry →</a>
					</div>
				{:else}
					<div class="reported">{submitted.message}</div>
				{/if}
			{:else}
				<button class="report-btn" onclick={reportFraud}>⚑ Report fraud to the registry</button>
				<p class="muted small">
					{data.providers.filter((p) => p.at_risk > 0).length} provider(s) flagged. Submitting adds
					them to the shared registry for everyone to see.
				</p>
			{/if}

			<h2>What was flagged</h2>
			<table>
				<thead><tr><th>Line</th><th>Rule</th><th>Detail</th><th class="r">At risk</th></tr></thead>
				<tbody>
					{#each data.findings.filter((f) => f.severity === 'breach') as f}
						<tr>
							<td class="num">{f.line}</td>
							<td><strong>{f.rule}</strong></td>
							<td>{f.detail}</td>
							<td class="num r">{f.at_risk ? money(f.at_risk) : '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="reported clean">No fraud detected in this batch — nothing to report.</div>
		{/if}
	</section>
{/if}

<style>
	.drop {
		border: 1.5px dashed var(--line-2);
		padding: 48px 24px;
		text-align: center;
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		transition: border-color 0.15s, background 0.15s;
	}
	.drop.dragging {
		border-color: var(--ink);
		background: var(--paper);
	}
	.big {
		font-size: 17px;
		font-weight: 500;
		margin: 0;
	}
	.picks {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 10px;
		align-items: center;
		margin-top: 6px;
	}
	.btn,
	.link {
		font-size: 13px;
		border: 1px solid var(--line-2);
		padding: 9px 16px;
		cursor: pointer;
		color: var(--ink);
	}
	.btn:hover,
	.link:hover {
		background: var(--hover);
		border-color: var(--ink);
		text-decoration: none;
	}
	.btn input {
		display: none;
	}
	.screening {
		margin-top: 28px;
	}
	.result {
		margin-top: 36px;
	}
	.metrics {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 26px;
		padding: 26px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
		max-width: 540px;
	}
	.metric.flag .v {
		color: var(--critical);
	}
	.report-btn {
		margin: 28px 0 6px;
		background: var(--critical);
		color: #fff;
		border-color: var(--critical);
		font-size: 14px;
		padding: 12px 22px;
	}
	.report-btn:hover {
		background: #8f1e17;
		border-color: #8f1e17;
	}
	.reported {
		margin: 28px 0;
		padding: 14px 18px;
		border: 1px solid var(--line-2);
		font-size: 14px;
	}
	.reported.ok {
		border-color: var(--clear);
		color: var(--clear);
	}
	.reported.clean {
		color: var(--ink-3);
	}
	.small {
		font-size: 12px;
		margin: 0 0 10px;
	}
	h2 {
		margin: 32px 0 16px;
	}
	@media (max-width: 560px) {
		.drop {
			padding: 32px 16px;
		}
		.metrics {
			grid-template-columns: repeat(2, 1fr);
			gap: 18px 24px;
		}
	}
</style>
