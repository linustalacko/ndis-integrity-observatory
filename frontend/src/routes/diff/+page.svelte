<script lang="ts">
	import { api, type DiffResp } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let snaps = $state<string[]>([]);
	let a = $state('');
	let b = $state('');
	let data = $state<DiffResp | null>(null);

	$effect(() => {
		api.snapshots().then((d) => {
			snaps = d.snapshots;
			if (snaps.length >= 2) {
				a = snaps[snaps.length - 2];
				b = snaps[snaps.length - 1];
			}
		});
	});
	$effect(() => {
		if (a && b) api.diff(a, b).then((d) => (data = d));
	});
</script>

<Header title="Register diff" lede="What was added between snapshots — and what was quietly removed." />

<div class="picker">
	<label>From <select bind:value={a}>{#each snaps as s}<option value={s}>{s}</option>{/each}</select></label>
	<span class="arrow muted">→</span>
	<label>To <select bind:value={b}>{#each snaps as s}<option value={s}>{s}</option>{/each}</select></label>
</div>

{#if snaps.length < 2}
	<p class="muted">Need at least two register snapshots to compare.</p>
{:else if data}
	<div class="cols">
		<section>
			<h2>＋ New on register <span class="muted num">({data.new.length})</span></h2>
			<table>
				<thead><tr><th>Type</th><th>Name</th><th>State</th><th>Effective</th></tr></thead>
				<tbody>
					{#each data.new as r}
						<tr><td class="muted">{r.type.replace('ER - ', '')}</td><td>{r.name}</td><td>{r.state}</td><td class="num muted">{r.date_from}</td></tr>
					{/each}
				</tbody>
			</table>
		</section>
		<section>
			<h2>－ Removed <span class="muted num">({data.gone.length})</span></h2>
			<table>
				<thead><tr><th>Type</th><th>Name</th><th>State</th><th>Last seen</th></tr></thead>
				<tbody>
					{#each data.gone as r}
						<tr><td class="muted">{r.type.replace('ER - ', '')}</td><td>{r.name}</td><td>{r.state}</td><td class="num muted">{r.last_seen}</td></tr>
					{/each}
				</tbody>
			</table>
		</section>
	</div>
{/if}

<style>
	.picker {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 16px;
		margin-bottom: 34px;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 6px;
		font-size: 11px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--ink-3);
	}
	select {
		width: 150px;
	}
	.arrow {
		padding-bottom: 11px;
	}
	.cols {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 44px;
		align-items: start;
	}
	h2 {
		margin-bottom: 14px;
	}
	@media (max-width: 860px) {
		.cols {
			grid-template-columns: 1fr;
			gap: 32px;
		}
	}
</style>
