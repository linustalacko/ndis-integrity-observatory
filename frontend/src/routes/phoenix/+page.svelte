<script lang="ts">
	import { api, type PhoenixResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let tier = $state('high');
	let data = $state<PhoenixResp | null>(null);
	$effect(() => {
		api.phoenix(tier).then((d) => (data = d));
	});
	const tiers = [
		{ k: 'high', label: 'High only' },
		{ k: 'medium', label: 'High + medium' },
		{ k: 'all', label: 'All' }
	];
</script>

<Header
	kicker="Sanctioned, yet an ABN is active"
	title="Phoenix watch"
	lede="Sanctioned entities whose name or ABN matches an active ABN registered after the sanction. Confidence is driven by name rarity, geography and match type — a common name with hundreds of namesakes scores low. Every row is a lead to verify, never an allegation."
/>

{#if data}
	<section class="tiers">
		<div class="metric"><span class="v num">{data.counts.high ?? 0}</span><span class="k"><span class="dot high"></span> High confidence</span></div>
		<div class="metric"><span class="v num">{data.counts.medium ?? 0}</span><span class="k"><span class="dot medium"></span> Medium</span></div>
		<div class="metric"><span class="v num">{data.counts.low ?? 0}</span><span class="k"><span class="dot low"></span> Low (likely collisions)</span></div>
	</section>

	<div class="controls">
		{#each tiers as t}
			<button class:active={tier === t.k} onclick={() => (tier = t.k)}>{t.label}</button>
		{/each}
		<span class="muted count">{data.leads.length} shown</span>
	</div>

	<table>
		<thead>
			<tr>
				<th>Conf.</th><th>Name</th><th>Sanction</th><th>Effective</th>
				<th>ABN</th><th>Namesakes</th><th>Geo</th><th>ABR record</th>
			</tr>
		</thead>
		<tbody>
			{#each data.leads as l}
				<tr>
					<td>
						<div class="conf">
							<span class="num">{Math.round(l.confidence)}</span>
							<div class="bar"><span style="width:{l.confidence}%"></span></div>
						</div>
					</td>
					<td><strong>{l.name}</strong></td>
					<td><span class="tag">{l.type.replace('ER - ', '')}</span></td>
					<td class="num muted">{l.sanction_date}</td>
					<td class="mono">{l.abn}</td>
					<td class="num" class:warn={l.namesakes === 1}>{l.namesakes}</td>
					<td>{l.geo}</td>
					<td class="muted note">{l.note}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	<p class="src muted">
		Sources: NDIS Commission compliance register (data.gov.au) + ABN Bulk Extract (Australian
		Business Register). Confidence is a triage signal, not proof.
	</p>
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.tiers {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 28px;
		padding: 26px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
		max-width: 620px;
	}
	.metric .k {
		display: flex;
		align-items: center;
		gap: 7px;
	}
	.controls {
		display: flex;
		gap: 8px;
		align-items: center;
		margin: 28px 0 18px;
	}
	.count {
		margin-left: 8px;
		font-size: 12.5px;
	}
	.conf {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 56px;
	}
	.note {
		max-width: 280px;
		font-size: 12px;
	}
	.warn {
		font-weight: 600;
	}
	.src {
		margin-top: 20px;
		font-size: 12px;
		max-width: 680px;
	}
</style>
