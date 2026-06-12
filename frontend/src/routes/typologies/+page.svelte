<script lang="ts">
	import { api, type TypologyResp, type Sample } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let data = $state<TypologyResp | null>(null);
	let selected = $state('');
	let samples = $state<Sample[]>([]);

	$effect(() => {
		api.typologies().then((d) => {
			data = d;
			if (d.distribution.length && !selected) pick(d.distribution[0].typology);
		});
	});
	async function pick(t: string) {
		selected = t;
		samples = (await api.typologySamples(t)).samples;
	}
	const max = $derived(Math.max(1, ...(data?.distribution.map((d) => d.n) ?? [1])));
</script>

<Header title="Typologies" lede="Conduct behind each action, classified — counted only when quote-verified." />

{#if data}
	<p class="stat muted">
		{data.verified.toLocaleString()} verified of {data.classified.toLocaleString()} ({Math.round(
			(data.verified / data.classified) * 100
		)}%)
	</p>
	<div class="grid">
		<div class="dist">
			{#each data.distribution as d}
				<button class="trow" class:active={selected === d.typology} onclick={() => pick(d.typology)}>
					<span class="tname">{d.typology}</span>
					<div class="bar"><span style="width:{(d.n / max) * 100}%"></span></div>
					<span class="tn num">{d.n}</span>
				</button>
			{/each}
		</div>
		<div class="samples">
			<div class="label">Verified examples — {selected}</div>
			<div class="slist">
				{#each samples as s}
					<div class="sample">
						<div class="shead">
							<strong>{s.name}</strong>
							<span class="muted num">{s.type.replace('ER - ', '')} · {s.date_from}</span>
						</div>
						<p class="quote">“{s.quote}”</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.stat {
		margin: 0 0 26px;
		font-size: 12.5px;
	}
	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 44px;
		align-items: start;
	}
	.dist {
		display: flex;
		flex-direction: column;
		border-top: 1px solid var(--line);
	}
	.trow {
		display: grid;
		grid-template-columns: 1fr 90px 46px;
		align-items: center;
		gap: 14px;
		border: none;
		border-bottom: 1px solid var(--line);
		background: none;
		padding: 12px 6px;
		text-align: left;
		font-size: 13px;
	}
	.trow:hover {
		background: var(--paper);
	}
	.trow.active .tname {
		font-weight: 600;
	}
	.tn {
		text-align: right;
		font-size: 13px;
	}
	.samples {
		position: sticky;
		top: 48px;
	}
	.slist {
		margin-top: 14px;
		display: flex;
		flex-direction: column;
		gap: 0;
		max-height: 72vh;
		overflow-y: auto;
	}
	.sample {
		border-bottom: 1px solid var(--line);
		padding: 13px 0;
	}
	.shead {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 5px;
		font-size: 13px;
	}
	.quote {
		font-size: 12.5px;
		line-height: 1.5;
		color: var(--ink-2);
		margin: 0;
		font-style: italic;
	}
	@media (max-width: 860px) {
		.grid {
			grid-template-columns: 1fr;
			gap: 30px;
		}
		.samples {
			position: static;
		}
	}
</style>
