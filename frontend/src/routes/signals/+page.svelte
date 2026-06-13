<script lang="ts">
	import { api, type SignalsResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let data = $state<SignalsResp | null>(null);
	let tab = $state<'regions' | 'operators' | 'families'>('regions');
	$effect(() => {
		api.signals().then((d) => (data = d));
	});
	function pct(n: number | null) {
		if (n === null || n === undefined) return '—';
		return `${n > 0 ? '+' : ''}${(n * 100).toFixed(0)}%`;
	}
	function money(n: number | null) {
		if (!n) return '—';
		if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
		return `$${Math.round(n / 1e3)}k`;
	}
	const regions = $derived(data?.regions.slice(0, 25) ?? []);
</script>

<Header
	title="Fraud signals"
	lede="Where the numbers don't add up. Population anomalies and entity networks that point to likely fraud — risk signals to investigate, not proof."
/>

{#if data}
	<div class="tabs">
		<button class:active={tab === 'regions'} onclick={() => (tab = 'regions')}>Region anomalies</button>
		<button class:active={tab === 'operators'} onclick={() => (tab = 'operators')}>Multi-ABN operators</button>
		<button class:active={tab === 'families'} onclick={() => (tab = 'families')}>Family networks</button>
	</div>

	{#if tab === 'regions'}
		<p class="explain muted">
			Service districts ranked by a composite of provider-count growth above the national rate
			({data.national_growth}% over the period), market fragmentation (falling top-10 share), and
			spend per provider. Fast provider growth without matching demand is the ghost-provider
			signature.
		</p>
		<table>
			<thead>
				<tr><th>Risk</th><th>District</th><th class="r">Providers</th><th class="r">Growth</th><th class="r">vs nat.</th><th class="r">Frag.</th><th class="r">$/provider</th></tr>
			</thead>
			<tbody>
				{#each regions as r}
					<tr>
						<td>
							<div class="conf"><span class="num">{r.risk.toFixed(0)}</span>
								<div class="bar"><span style="width:{r.risk}%"></span></div></div>
						</td>
						<td><strong>{r.district}</strong> <span class="muted">{r.state}</span></td>
						<td class="num r">{r.providers_first}→{r.providers_last}</td>
						<td class="num r">{pct(r.growth)}</td>
						<td class="num r" class:warn={r.excess_growth > 0.05}>{pct(r.excess_growth)}</td>
						<td class="num r">{r.frag !== null && r.frag > 0 ? pct(r.frag) : '—'}</td>
						<td class="num r">{money(r.spend_per_provider)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else if tab === 'operators'}
		<p class="explain muted">
			Sanctioned people linked to several active ABNs (confidence-scored — common-name clashes
			excluded). One operator behind many businesses is the syndicate signature seen in NDIS
			prosecutions.
		</p>
		<table>
			<thead><tr><th>Name</th><th>Status</th><th class="r">ABNs</th><th class="r">Post-ban</th><th>Location</th></tr></thead>
			<tbody>
				{#each data.operators as o}
					<tr>
						<td><strong>{o.name}</strong></td>
						<td>{#if o.sanctioned}<span class="tag">{o.type.replace('ER - ', '')}</span>{:else}<span class="muted">—</span>{/if}</td>
						<td class="num r big">{o.n_abns}</td>
						<td class="num r" class:warn={o.n_post_ban > 0}>{o.n_post_ban}</td>
						<td class="muted">{o.state} {o.postcode}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<p class="explain muted">
			Two or more different people sharing a surname and a postcode, where at least one is
			sanctioned — the family / associate network signature. Verify identity before relying.
		</p>
		<div class="fam">
			{#each data.families as f}
				<div class="fcard">
					<div class="fhead">
						<strong>{f.surname}</strong>
						<span class="muted">{f.postcode} {f.state}</span>
						<span class="tag">{f.n_sanctioned} sanctioned</span>
					</div>
					{#each f.members as m}
						<div class="member">
							<span class="dot {m.type.includes('Banning') ? 'critical' : 'elevated'}"></span>
							<span class="mname">{m.name}</span>
							<span class="muted mtype">{m.type.replace('ER - ', '')} · {m.date_from}</span>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	{/if}
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.tabs {
		display: flex;
		gap: 8px;
		margin-bottom: 22px;
	}
	.explain {
		font-size: 12.5px;
		line-height: 1.55;
		max-width: 720px;
		margin: 0 0 24px;
	}
	.r {
		text-align: right;
	}
	.conf {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 52px;
	}
	.warn {
		font-weight: 600;
	}
	.big {
		font-weight: 600;
		font-size: 15px;
	}
	.fam {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}
	.fcard {
		border: 1px solid var(--line);
		padding: 16px 18px;
	}
	.fhead {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 12px;
		font-size: 15px;
	}
	.member {
		display: flex;
		align-items: center;
		gap: 9px;
		padding: 5px 0;
		font-size: 13px;
	}
	.mname {
		font-weight: 500;
	}
	.mtype {
		font-size: 11.5px;
		margin-left: auto;
	}
	@media (max-width: 820px) {
		.fam {
			grid-template-columns: 1fr;
		}
	}
</style>
