<script lang="ts">
	import { api, type CheckResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let q = $state('');
	let res = $state<CheckResp | null>(null);
	let loading = $state(false);
	const examples = ['Touch & Care', 'Krista Vegter', 'Aussie Life Care', 'Fictional Wellness Co'];

	async function run(query: string) {
		q = query;
		if (!query.trim()) return;
		loading = true;
		try {
			res = await api.check(query);
		} finally {
			loading = false;
		}
	}
	const riskClass = $derived(res?.risk ?? 'clear');
</script>

<Header
	title="Provider check"
	lede="Name or ABN in — a verdict, the full enforcement history, and any post-sanction ABNs."
/>

<form
	onsubmit={(e) => {
		e.preventDefault();
		run(q);
	}}
>
	<div class="searchrow">
		<input type="text" bind:value={q} placeholder="Provider name or ABN" autocomplete="off" />
		<button class="primary" type="submit">Check</button>
	</div>
	<div class="examples">
		{#each examples as ex}
			<button type="button" class="ghost" onclick={() => run(ex)}>{ex}</button>
		{/each}
	</div>
</form>

{#if loading}
	<p class="muted">Checking…</p>
{:else if res}
	<div class="verdict {riskClass}">
		<span class="dot {riskClass}"></span>
		<span class="vtext">{res.verdict}</span>
	</div>

	{#if res.sanctions.length}
		<section>
			<div class="label">Active sanctions</div>
			{#each res.sanctions as s}
				<div class="rec">
					<div class="rec-head">
						<strong>{s.type.replace('ER - ', '')}</strong>
						<span class="muted num">effective {s.date_from}</span>
						{#if s.city || s.state}<span class="muted">· {s.city} {s.state} {s.postcode}</span>{/if}
					</div>
					<p class="detail">{s.detail}</p>
					{#if s.first_seen}<p class="prov muted">On register {s.first_seen} → {s.last_seen} · NDIS Commission via data.gov.au</p>{/if}
				</div>
			{/each}
		</section>
	{/if}

	{#if res.compliance_notices.length}
		<section>
			<div class="label">Compliance notices ({res.compliance_notices.length})</div>
			{#each res.compliance_notices as n}
				<div class="rec">
					<div class="rec-head"><span class="muted num">{n.date_from}</span>{#if n.city}<span class="muted">· {n.city} {n.state}</span>{/if}</div>
					<p class="detail">{n.detail}</p>
					{#if n.first_seen}<p class="prov muted">On register {n.first_seen} → {n.last_seen}</p>{/if}
				</div>
			{/each}
		</section>
	{/if}

	{#if res.phoenix_links.length}
		<section>
			<div class="label">Post-sanction ABN links — verify before relying</div>
			<table>
				<thead><tr><th>ABN</th><th>Conf.</th><th>Namesakes</th><th>Geo</th><th>Detail</th></tr></thead>
				<tbody>
					{#each res.phoenix_links as p}
						<tr>
							<td class="mono">{p.abn}</td>
							<td class="num">{Math.round(p.confidence)}</td>
							<td class="num">{p.name_freq}</td>
							<td>{p.geo}</td>
							<td class="muted">{p.note}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
	{/if}

	<p class="disclaimer muted">Public register data. A clear result is not endorsement; phoenix links are leads for verification.</p>
{/if}

<style>
	.searchrow {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 10px;
		max-width: 640px;
	}
	.examples {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 14px;
	}
	.verdict {
		display: flex;
		align-items: center;
		gap: 14px;
		margin: 38px 0 30px;
		padding-bottom: 24px;
		border-bottom: 1px solid var(--line);
	}
	.verdict .dot {
		width: 12px;
		height: 12px;
		flex: none;
	}
	.vtext {
		font-size: 23px;
		font-weight: 600;
		letter-spacing: -0.02em;
	}
	.verdict.critical .vtext {
		color: var(--critical);
	}
	.verdict.elevated .vtext {
		color: var(--elevated);
	}
	.verdict.clear .vtext {
		color: var(--clear);
	}
	section {
		margin-bottom: 34px;
	}
	section .label {
		margin-bottom: 14px;
	}
	.rec {
		border-left: 2px solid var(--line-2);
		padding: 2px 0 2px 16px;
		margin-bottom: 16px;
	}
	.rec-head {
		display: flex;
		gap: 12px;
		align-items: baseline;
		margin-bottom: 5px;
	}
	.detail {
		font-size: 13px;
		line-height: 1.55;
		color: var(--ink-2);
		margin: 0;
	}
	.prov { font-size: 11px; margin: 4px 0 0; }
	.disclaimer {
		font-size: 12px;
		line-height: 1.55;
		max-width: 680px;
		border-top: 1px solid var(--line);
		padding-top: 18px;
	}
</style>
