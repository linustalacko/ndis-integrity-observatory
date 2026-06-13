<script lang="ts">
	import { api, type MoneyResp } from '$lib/api';
	import { money as m } from '$lib/format';
	import Header from '$lib/Header.svelte';

	let data = $state<MoneyResp | null>(null);
	$effect(() => {
		api.money().then((d) => (data = d));
	});

	const byYear = $derived.by(() => {
		if (!data) return [];
		const y = new Map<string, number>();
		for (const c of data.cases) {
			const yr = c.date.slice(0, 4);
			y.set(yr, (y.get(yr) ?? 0) + c.amount);
		}
		return [...y.entries()].sort().map(([year, total]) => ({ year, total }));
	});
	const maxYear = $derived(Math.max(1, ...byYear.map((y) => y.total)));
</script>

<Header title="Fraud value" lede="The dollar scale of NDIS fraud, from public data." />

{#if data}
	<section class="bands">
		<div class="band">
			<div class="label">Estimated annual leakage</div>
			<div class="bigrange num">{m(data.systemic.low)} – {m(data.systemic.high)}<span class="per">/yr</span></div>
			<div class="muted basis">{data.systemic.basis} · {data.systemic.source}</div>
		</div>
		<div class="band">
			<div class="label">Prosecuted / charged to date</div>
			<div class="bigrange num">{m(data.case_total)}</div>
			<div class="muted basis">{data.case_count} cases · Fraud Fusion Taskforce (AFP) releases</div>
		</div>
	</section>

	<p class="gap muted">
		The gap is the point: less than {Math.round((data.case_total / data.systemic.low) * 100)}% of one year's
		estimated leakage has been charged. Brand-new fraud only becomes visible once live claims are
		screened — see the Claims lab.
	</p>

	<section class="block">
		<h2>Charged amount by year</h2>
		<div class="years">
			{#each byYear as y}
				<div class="yr">
					<span class="yk num">{y.year}</span>
					<div class="bar"><span style="width:{(y.total / maxYear) * 100}%"></span></div>
					<span class="yv num">{m(y.total)}</span>
				</div>
			{/each}
		</div>
	</section>

	<section class="block">
		<h2>Cases</h2>
		<table>
			<thead><tr><th>Date</th><th>Amount</th><th>Status</th><th>Case</th></tr></thead>
			<tbody>
				{#each data.cases.slice().sort((a, b) => b.amount - a.amount) as c}
					<tr>
						<td class="num muted">{c.date}</td>
						<td class="num amt">{m(c.amount)}</td>
						<td><span class="tag">{c.kind}</span></td>
						<td><a href={c.url} target="_blank" rel="noreferrer">{c.title}</a></td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.bands {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 40px;
		padding: 28px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
	}
	.band {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.bigrange {
		font-size: 38px;
		font-weight: 600;
		letter-spacing: -0.03em;
		line-height: 1;
	}
	.per {
		font-size: 18px;
		color: var(--ink-3);
		margin-left: 4px;
	}
	.basis {
		font-size: 12px;
	}
	.gap {
		margin: 24px 0 0;
		font-size: 13.5px;
		line-height: 1.55;
		max-width: 660px;
	}
	.block {
		margin-top: 48px;
	}
	.block h2 {
		margin-bottom: 20px;
	}
	.years {
		display: flex;
		flex-direction: column;
		gap: 10px;
		max-width: 620px;
	}
	.yr {
		display: grid;
		grid-template-columns: 48px 1fr 64px;
		align-items: center;
		gap: 14px;
	}
	.yv {
		text-align: right;
		font-size: 13px;
	}
	.amt {
		font-weight: 600;
	}
	@media (max-width: 760px) {
		.bands {
			grid-template-columns: 1fr;
			gap: 26px;
		}
		.bigrange {
			font-size: 30px;
		}
	}
</style>
