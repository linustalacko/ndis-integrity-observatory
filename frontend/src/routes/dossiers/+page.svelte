<script lang="ts">
	import { api } from '$lib/api';
	import Header from '$lib/Header.svelte';

	let leads = $state<{ name: string; confidence: number }[]>([]);
	let selected = $state('');
	let markdown = $state('');
	let loading = $state(false);

	$effect(() => {
		api.dossierList().then((d) => {
			leads = d.leads;
			if (leads.length && !selected) load(leads[0].name);
		});
	});

	async function load(name: string) {
		selected = name;
		loading = true;
		try {
			markdown = (await api.dossier(name)).markdown;
		} finally {
			loading = false;
		}
	}
	function download() {
		const blob = new Blob([markdown], { type: 'text/markdown' });
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.download = `dossier_${selected.slice(0, 40)}.md`;
		a.click();
	}
	// tiny markdown -> html for headings, bold, lists, links
	const html = $derived.by(() => {
		return markdown
			.split('\n')
			.map((line) => {
				if (line.startsWith('# ')) return `<h2>${esc(line.slice(2))}</h2>`;
				if (line.startsWith('## ')) return `<h3>${esc(line.slice(3))}</h3>`;
				if (line.startsWith('> ')) return `<blockquote>${inline(line.slice(2))}</blockquote>`;
				if (/^\d+\.\s/.test(line)) return `<div class="li num-li">${inline(line)}</div>`;
				if (line.startsWith('- ')) return `<div class="li">${inline(line.slice(2))}</div>`;
				if (line.trim() === '') return '';
				return `<p>${inline(line)}</p>`;
			})
			.join('');
	});
	function esc(s: string) {
		return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}
	function inline(s: string) {
		return esc(s)
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noreferrer">$1</a>');
	}
</script>

<Header title="Lead dossiers" lede="Everything known about one sanctioned entity, in one cited document." />

<div class="grid">
	<aside class="leads">
		<div class="label">High-confidence leads ({leads.length})</div>
		<div class="leadlist">
			{#each leads as l}
				<button class="lead" class:active={selected === l.name} onclick={() => load(l.name)}>
					<span class="lname">{l.name}</span>
					<span class="lconf num">{Math.round(l.confidence)}</span>
				</button>
			{/each}
		</div>
	</aside>
	<article>
		{#if loading}
			<p class="muted">Loading…</p>
		{:else if markdown}
			<div class="actions">
				<button onclick={download}>Download Markdown</button>
			</div>
			<div class="doc">{@html html}</div>
		{/if}
	</article>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: 270px 1fr;
		gap: 40px;
		align-items: start;
	}
	.leads {
		position: sticky;
		top: 48px;
	}
	.leadlist {
		margin-top: 14px;
		display: flex;
		flex-direction: column;
		max-height: 70vh;
		overflow-y: auto;
		border-top: 1px solid var(--line);
	}
	.lead {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 10px;
		border: none;
		border-bottom: 1px solid var(--line);
		background: none;
		padding: 11px 4px;
		text-align: left;
		font-size: 13px;
	}
	.lead:hover {
		background: var(--paper);
	}
	.lead.active {
		background: var(--ink);
		color: var(--bg);
	}
	.lname {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.lconf {
		font-size: 12px;
		opacity: 0.7;
		flex: none;
	}
	.actions {
		margin-bottom: 22px;
	}
	.doc :global(h2) {
		font-size: 22px;
		margin: 0 0 6px;
	}
	.doc :global(h3) {
		font-size: 13px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-3);
		margin: 30px 0 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--line);
	}
	.doc :global(blockquote) {
		margin: 14px 0;
		padding: 14px 16px;
		background: var(--paper);
		border-left: 2px solid var(--ink);
		font-size: 12.5px;
		line-height: 1.55;
		color: var(--ink-2);
	}
	.doc :global(p) {
		font-size: 13.5px;
		line-height: 1.6;
		margin: 4px 0;
	}
	.doc :global(.li) {
		font-size: 13px;
		line-height: 1.55;
		padding: 4px 0 4px 16px;
		position: relative;
		color: var(--ink-2);
	}
	.doc :global(.li)::before {
		content: '·';
		position: absolute;
		left: 4px;
		color: var(--ink-3);
	}
	.doc :global(.num-li)::before {
		content: '';
	}
	.doc :global(strong) {
		color: var(--ink);
		font-weight: 600;
	}
	.doc :global(.li strong) {
		font-weight: 600;
	}
	@media (max-width: 820px) {
		.grid {
			grid-template-columns: 1fr;
			gap: 24px;
		}
		.leads {
			position: static;
		}
	}
</style>
