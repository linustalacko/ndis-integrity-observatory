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

	const TYPE_ORDER = [
		'ER - Banning Order',
		'ER - Revocation of registration',
		'ER - Suspension of registration',
		'ER - Refusal to re-register',
		'ER - Compliance notice',
		'ER - Enforceable Undertaking'
	];
	const monthlyRows = $derived.by(() => {
		if (!data) return [];
		const byMonth = new Map<string, Record<string, number>>();
		for (const r of data.monthly) {
			const row = byMonth.get(r.month) ?? { month: r.month as unknown as number };
			row[r.type] = (Number(row[r.type]) || 0) + r.n;
			byMonth.set(r.month, row);
		}
		return [...byMonth.values()];
	});
	const series = TYPE_ORDER.map((key, i) => ({ key, shade: i / (TYPE_ORDER.length - 1) }));
	const maxState = $derived(Math.max(1, ...(data?.by_state.map((s) => s.n) ?? [1])));
	const maxSpot = $derived(Math.max(1, ...(data?.hotspots.map((s) => s.n) ?? [1])));
</script>

<Header
	kicker="National enforcement landscape"
	title="The NDIS provider integrity record, assembled."
	lede="Every enforcement action the NDIS Commission has published, tracked across snapshots and joined to the business register — the analytic view the regulator's own site does not provide."
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
			<span class="v num">{data.totals.actions.toLocaleString()}</span><span class="k"
				>Enforcement actions</span
			>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.banning_orders.toLocaleString()}</span><span class="k"
				>Banning orders</span
			>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.compliance_notices.toLocaleString()}</span><span class="k"
				>Compliance notices</span
			>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.revocations.toLocaleString()}</span><span class="k"
				>Revocations</span
			>
		</div>
		<div class="metric">
			<span class="v num">{data.totals.phoenix_high}</span><span class="k"
				>High-conf. phoenix leads</span
			>
		</div>
	</section>

	<p class="snapnote muted">
		{data.snapshots.count} register snapshots tracked, {data.snapshots.from} → {data.snapshots.to}.
	</p>

	<section class="block">
		<div class="block-head">
			<h2>Enforcement actions by month</h2>
			<div class="legend">
				{#each series as s}
					<span class="leg"
						><i style="background:hsl(0 0% {Math.round(8 + s.shade * 70)}%)"></i>{s.key.replace(
							'ER - ',
							''
						)}</span
					>
				{/each}
			</div>
		</div>
		<BarChart data={monthlyRows} {series} labels={(d) => String(d.month)} height={280} />
		<p class="axisnote muted">
			Monthly, by date effective. The mid-2025 and early-2026 spikes are the Fraud Fusion Taskforce
			enforcement waves.
		</p>
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
	.snapnote {
		margin: 16px 0 0;
		font-size: 12.5px;
	}
	.block {
		margin-top: 52px;
	}
	.block-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 22px;
		gap: 24px;
		flex-wrap: wrap;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
	}
	.leg {
		font-size: 11px;
		color: var(--ink-3);
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.leg i {
		width: 9px;
		height: 9px;
		display: inline-block;
	}
	.axisnote {
		margin-top: 14px;
		font-size: 12px;
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
