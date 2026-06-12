<script lang="ts">
	// Minimal monochrome stacked-bar chart. SVG, no dependencies.
	type Series = { key: string; shade: number }; // shade 0..1 -> grey
	let {
		data,
		series,
		labels,
		height = 260,
		grid = 4
	}: {
		data: Record<string, number>[]; // each row: { label, [seriesKey]: n }
		series: Series[];
		labels: (d: Record<string, number>) => string;
		height?: number;
		grid?: number;
	} = $props();

	const totals = $derived(data.map((d) => series.reduce((s, x) => s + (Number(d[x.key]) || 0), 0)));
	const max = $derived(Math.max(1, ...totals));
	const niceMax = $derived(Math.ceil(max / grid) * grid || grid);
	const grey = (s: number) => `hsl(0 0% ${Math.round(8 + s * 70)}%)`;
</script>

<div class="chart" style="height:{height}px">
	<div class="yaxis">
		{#each Array(grid + 1) as _, i (i)}
			{@const v = Math.round((niceMax / grid) * (grid - i))}
			<div class="ytick"><span class="num">{v}</span></div>
		{/each}
	</div>
	<div class="plot">
		<div class="bars">
			{#each data as d, i (i)}
				<div class="col" title={labels(d)}>
					<div class="stack">
						{#each series as s (s.key)}
							{@const n = Number(d[s.key]) || 0}
							{#if n > 0}
								<div
									class="seg"
									style="height:{(n / niceMax) * 100}%; background:{grey(s.shade)}"
								></div>
							{/if}
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.chart {
		display: grid;
		grid-template-columns: 38px 1fr;
		gap: 8px;
		width: 100%;
	}
	.yaxis {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}
	.ytick {
		font-size: 10.5px;
		color: var(--ink-3);
		text-align: right;
		transform: translateY(-6px);
	}
	.plot {
		border-bottom: 1px solid var(--line-2);
		border-left: 1px solid var(--line);
		position: relative;
	}
	.bars {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: flex-end;
		gap: 2px;
		padding: 0 2px;
	}
	.col {
		flex: 1;
		height: 100%;
		display: flex;
		align-items: flex-end;
		min-width: 0;
	}
	.stack {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column-reverse;
	}
	.seg {
		width: 100%;
		transition: opacity 0.12s;
	}
	.col:hover .seg {
		opacity: 0.7;
	}
</style>
