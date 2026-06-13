<script lang="ts">
	import { api, type Overview } from '$lib/api';
	import Header from '$lib/Header.svelte';
	import BarChart from '$lib/BarChart.svelte';

	let data = $state<Overview | null>(null);
	let error = $state<string | null>(null);
	$effect(() => {
		api
			.overview()
			.then((d) => (data = d))
			.catch((e) => (error = String(e)));
	});

	const monthlyRows = $derived.by(() => {
		if (!data) return [];
		const byMonth = new Map<string, Record<string, number>>();
		for (const r of data.monthly) {
			const row = byMonth.get(r.month) ?? { month: r.month as unknown as number, n: 0 };
			row.n = (Number(row.n) || 0) + r.n;
			byMonth.set(r.month, row);
		}
		return [...byMonth.values()];
	});
	const series = [{ key: 'n', shade: 0 }];
	const maxState = $derived(Math.max(1, ...(data?.by_state.map((s) => s.n) ?? [1])));
	const maxSpot = $derived(Math.max(1, ...(data?.hotspots.map((s) => s.n) ?? [1])));
</script>

<Header
	title="Overview"
	lede="Two jobs: surface banned operators who are quietly back in business, and screen live invoices for fraud as it happens."
/>

{#if error}
	<div class="card">
		Could not reach the API on :8000. <span class="muted">{error}</span>
	</div>
{:else if !data}
	<div class="muted">Loading…</div>
{:else}
	<section class="metrics">
		<div class="metric">
			<span class="v num">{data.totals.actions.toLocaleString()}</span><span class="k">Actions</span>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.banning_orders.toLocaleString()}</span><span class="k">Bans</span>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.compliance_notices.toLocaleString()}</span><span class="k">Notices</span>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.revocations.toLocaleString()}</span><span class="k">Revocations</span>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.phoenix_high}</span><span class="k">Phoenix leads</span>
		</div>
	</section>

	<section class="block">
		<h2 class="block-h">Actions by month</h2>
		<BarChart data={monthlyRows} {series} labels={(d) => String(d.month)} height={280} />
	</section>

	<div class="two">
		<section>
			<h2>By state</h2>
			<div class="rows">
				{#each data.by_state as s}
					<div class="row">
						<span class="rk">{s.state}</span>
						<div class="bar"><span style="width:{(s.n / maxState) * 100}%"></span></div>
						<span class="rv num">{s.n}</span>
					</div>
				{/each}
			</div>
		</section>
		<section>
			<h2>Hotspot postcodes</h2>
			<div class="rows">
				{#each data.hotspots as s}
					<div class="row">
						<span class="rk wide">{s.location}</span>
						<div class="bar"><span style="width:{(s.n / maxSpot) * 100}%"></span></div>
						<span class="rv num">{s.n}</span>
					</div>
				{/each}
			</div>
		</section>
	</div>
{/if}

<style>
	.metrics {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 28px;
		padding: 28px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
	}
	.block {
		margin-top: 48px;
	}
	.block-h {
		margin-bottom: 22px;
	}
	.two {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 52px;
		margin-top: 52px;
	}
	.two h2 {
		margin-bottom: 18px;
	}
	.rows {
		display: flex;
		flex-direction: column;
		gap: 9px;
	}
	.row {
		display: grid;
		grid-template-columns: 96px 1fr 42px;
		align-items: center;
		gap: 12px;
	}
	.rk {
		font-size: 13px;
		color: var(--ink-2);
	}
	.rk.wide {
		font-size: 12px;
	}
	.rv {
		text-align: right;
		font-size: 13px;
	}
	@media (max-width: 900px) {
		.metrics {
			grid-template-columns: repeat(2, 1fr);
			gap: 22px;
		}
		.two {
			grid-template-columns: 1fr;
			gap: 36px;
		}
	}
</style>
