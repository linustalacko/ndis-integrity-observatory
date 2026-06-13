<script lang="ts">
	import { api, type RegistryResp } from '$lib/api';
	import { money } from '$lib/format';
	import Header from '$lib/Header.svelte';

	let data = $state<RegistryResp | null>(null);
	let open = $state<string | null>(null);
	$effect(() => {
		api.registry().then((d) => (data = d));
	});
</script>

<Header
	title="Fraud registry"
	lede="Provider fraud reported by the community. Each entry was flagged by the screening rules, then submitted. User-reported and rule-flagged — verify independently."
/>

{#if data}
	<section class="metrics">
		<div class="metric flag"><span class="v num">{money(data.total_at_risk)}</span><span class="k">Total flagged</span></div>
		<div class="metric"><span class="v num">{data.count}</span><span class="k">Reports</span></div>
		<div class="metric"><span class="v num">{data.providers}</span><span class="k">Providers</span></div>
		<div class="metric"><span class="v num">{data.sanctioned}</span><span class="k">Already banned</span></div>
	</section>

	{#if data.count === 0}
		<p class="empty muted">
			No reports yet. <a href="/report">Report fraud →</a>
		</p>
	{:else}
		<div class="list">
			{#each data.reports as r}
				<div class="item">
					<button class="row" onclick={() => (open = open === r.report_id ? null : r.report_id)}>
						<span class="prov">
							<strong>{r.provider_name}</strong>
							{#if r.already_sanctioned}<span class="tag crit">already banned</span>{/if}
						</span>
						<span class="loc muted">{r.state}{r.postcode ? ' ' + r.postcode : ''}</span>
						<span class="svc muted">{r.services}</span>
						<span class="rules">{#each r.rules as rule}<span class="tag">{rule}</span>{/each}</span>
						<span class="amt num">{money(r.at_risk)}</span>
					</button>
					{#if open === r.report_id}
						<div class="body">
							<div class="meta">
								<span><span class="label">ABN</span> {r.provider_abn || '—'}</span>
								<span><span class="label">Billed</span> {money(r.billed)}</span>
								<span><span class="label">Breaches</span> {r.n_breaches}</span>
								<span><span class="label">Source</span> {r.source}</span>
							</div>
							{#if r.already_sanctioned}
								<p class="sanction">⚑ {r.already_sanctioned}</p>
							{/if}
							<table>
								<thead><tr><th>Line</th><th>Rule</th><th>Detail</th><th class="r">At risk</th></tr></thead>
								<tbody>
									{#each r.findings as f}
										<tr><td class="num">{f.line}</td><td><strong>{f.rule}</strong></td><td>{f.detail}</td><td class="num r">{f.at_risk ? money(f.at_risk) : '—'}</td></tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.metrics {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 28px;
		padding: 26px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
		margin-bottom: 8px;
		max-width: 640px;
	}
	.metric.flag .v {
		color: var(--critical);
	}
	.empty {
		margin-top: 28px;
	}
	.list {
		margin-top: 16px;
		border-top: 1px solid var(--line);
	}
	.item {
		border-bottom: 1px solid var(--line);
	}
	.row {
		display: grid;
		grid-template-columns: 1.6fr 0.7fr 1.4fr 1fr auto;
		align-items: center;
		gap: 16px;
		width: 100%;
		text-align: left;
		border: none;
		background: none;
		padding: 14px 4px;
		font-size: 13.5px;
	}
	.row:hover {
		background: var(--paper);
	}
	.prov {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.loc,
	.svc {
		font-size: 12px;
	}
	.amt {
		font-weight: 600;
		text-align: right;
		color: var(--critical);
	}
	.tag.crit {
		border-color: var(--critical);
		color: var(--critical);
	}
	.body {
		padding: 4px 18px 22px;
	}
	.meta {
		display: flex;
		gap: 28px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}
	.meta .label {
		display: block;
		margin-bottom: 2px;
	}
	.sanction {
		font-size: 12.5px;
		color: var(--critical);
		margin: 0 0 14px;
	}
	@media (max-width: 820px) {
		.row {
			grid-template-columns: 1fr auto auto;
		}
		.svc,
		.rules {
			display: none;
		}
		.prov {
			flex-wrap: wrap;
		}
		.body {
			padding: 4px 0 22px;
		}
	}
	@media (max-width: 640px) {
		.metrics {
			grid-template-columns: repeat(2, 1fr);
			gap: 18px 24px;
		}
	}
</style>
