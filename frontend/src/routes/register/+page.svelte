<script lang="ts">
	import { api, type Action } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let q = $state('');
	let actions = $state<Action[]>([]);
	let count = $state(0);
	let searched = $state(false);
	let open = $state<string | null>(null);

	async function run() {
		if (q.trim().length < 2) return;
		const r = await api.register(q);
		actions = r.actions;
		count = r.count;
		searched = true;
	}
	function badge(type: string) {
		if (type.includes('Banning')) return 'critical';
		if (type.includes('Revocation')) return 'elevated';
		return 'medium';
	}
</script>

<Header title="Register" lede="Search any provider or person. Full action history, with sources." />

<form
	onsubmit={(e) => {
		e.preventDefault();
		run();
	}}
>
	<div class="searchrow">
		<input type="text" bind:value={q} placeholder="Provider or person name, or ABN" autocomplete="off" />
		<button class="primary" type="submit">Search</button>
	</div>
</form>

{#if searched}
	<p class="count muted">{count} action{count === 1 ? '' : 's'} matched</p>
	<div class="list">
		{#each actions as a}
			<div class="item">
				<button class="row" onclick={() => (open = open === a.action_id ? null : a.action_id)}>
					<span class="dot {badge(a.type)}"></span>
					<span class="type">{a.type.replace('ER - ', '')}</span>
					<span class="name">{a.name}</span>
					<span class="loc muted">{a.state} {a.postcode}</span>
					<span class="date num muted">{a.date_from}</span>
				</button>
				{#if open === a.action_id}
					<div class="body">
						<div class="meta">
							<span><span class="label">ABN</span> {a.abn || '—'}</span>
							<span><span class="label">In force until</span> {a.date_to || 'ongoing'}</span>
							<span><span class="label">Tracked</span> {a.first_seen} → {a.last_seen}</span>
						</div>
						<p class="detail">{a.detail || 'No detail published.'}</p>
						<p class="src muted">Source: NDIS Commission compliance register via data.gov.au</p>
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}

<style>
	.searchrow {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 10px;
		max-width: 640px;
	}
	.count {
		margin: 24px 0 14px;
		font-size: 12.5px;
	}
	.list {
		border-top: 1px solid var(--line);
	}
	.item {
		border-bottom: 1px solid var(--line);
	}
	.row {
		display: grid;
		grid-template-columns: 12px 180px 1fr auto auto;
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
	.type {
		color: var(--ink-2);
		font-size: 12px;
	}
	.name {
		font-weight: 500;
	}
	.loc,
	.date {
		font-size: 12px;
	}
	.body {
		padding: 4px 22px 22px;
	}
	.meta {
		display: flex;
		gap: 28px;
		flex-wrap: wrap;
		margin-bottom: 14px;
	}
	.meta .label {
		display: block;
		margin-bottom: 2px;
	}
	.detail {
		font-size: 13px;
		line-height: 1.6;
		color: var(--ink-2);
		max-width: 760px;
		margin: 0 0 12px;
	}
	.src {
		font-size: 11.5px;
	}
	@media (max-width: 760px) {
		.row {
			grid-template-columns: 12px 1fr;
			gap: 8px;
		}
		.type,
		.loc,
		.date {
			display: none;
		}
	}
</style>
