<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	let { children } = $props();

	// Two groups: the product (find fraud) and the analyst tools (investigate).
	const groups = [
		{
			label: 'Find fraud',
			items: [
				{ href: '/registry', label: 'Fraud registry' },
				{ href: '/report', label: 'Report fraud' },
				{ href: '/check', label: 'Provider check' }
			]
		},
		{
			label: 'Intelligence',
			items: [
				{ href: '/', label: 'Overview' },
				{ href: '/signals', label: 'Fraud signals' },
				{ href: '/phoenix', label: 'Banned & back' }
			]
		},
		{
			label: 'Analyst tools',
			items: [
				{ href: '/money', label: 'Fraud value' },
				{ href: '/typologies', label: 'Typologies' },
				{ href: '/diff', label: 'Register diff' },
				{ href: '/dossiers', label: 'Dossiers' }
			]
		}
	];
	const current = $derived(page.url.pathname);

	// Mobile hamburger menu. Closes itself whenever the route changes.
	let menuOpen = $state(false);
	$effect(() => {
		current;
		menuOpen = false;
	});

	const SITE = 'NDIS Provider Integrity Observatory';
	const titles: Record<string, string> = Object.fromEntries(
		groups.flatMap((g) => g.items.map((i) => [i.href, i.label]))
	);
	const pageTitle = $derived(
		current === '/' ? SITE : titles[current] ? `${titles[current]} · ${SITE}` : SITE
	);
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<div class="shell">
	<aside class:open={menuOpen}>
		<div class="topbar">
			<a href="/" class="brand">
				<div class="mark">NDIS</div>
				<div class="title"><span>Provider Integrity</span> <span>Observatory</span></div>
				<div class="title-m">Integrity</div>
			</a>
			<button
				class="burger"
				class:open={menuOpen}
				aria-label={menuOpen ? 'Close menu' : 'Open menu'}
				aria-expanded={menuOpen}
				onclick={() => (menuOpen = !menuOpen)}
			>
				<span></span><span></span><span></span>
			</button>
		</div>
		<div class="panel">
			<nav>
				{#each groups as group}
					<div class="group-label">{group.label}</div>
					{#each group.items as item}
						<a href={item.href} class:active={current === item.href}>{item.label}</a>
					{/each}
				{/each}
			</nav>
			<div class="foot">
			<p class="muted">Public data. Leads for verification, not allegations.</p>
			<a
				class="gh"
				href="https://github.com/linustalacko/ndis-integrity-observatory"
				target="_blank"
				rel="noreferrer"
			>
				<svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
					<path
						d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"
					/>
				</svg>
				Open source on GitHub
			</a>
			</div>
		</div>
	</aside>
	<main>
		{@render children()}
	</main>
</div>

<style>
	.shell {
		display: grid;
		grid-template-columns: 248px 1fr;
		min-height: 100vh;
	}
	aside {
		border-right: 1px solid var(--line);
		padding: 34px 26px;
		display: flex;
		flex-direction: column;
		gap: 38px;
		position: sticky;
		top: 0;
		height: 100vh;
		overflow-y: auto;
	}
	.brand {
		display: flex;
		flex-direction: column;
		gap: 12px;
		color: inherit;
	}
	.brand:hover {
		text-decoration: none;
	}
	.mark {
		font-size: 12px;
		letter-spacing: 0.22em;
		font-weight: 600;
		border: 1px solid var(--ink);
		padding: 4px 8px;
		width: fit-content;
	}
	.title {
		font-size: 17px;
		font-weight: 600;
		letter-spacing: -0.02em;
		line-height: 1.25;
	}
	.title span {
		display: block;
	}
	/* compact brand label + hamburger: mobile only */
	.title-m,
	.burger {
		display: none;
	}
	/* on desktop the panel is transparent — nav and foot lay out directly in the aside */
	.panel {
		display: contents;
	}
	nav {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}
	.group-label {
		font-size: 10px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--ink-3);
		margin: 18px 0 6px;
		font-weight: 500;
	}
	.group-label:first-child {
		margin-top: 0;
	}
	nav a {
		font-size: 14px;
		color: var(--ink-2);
		padding: 8px 10px;
		margin: 0 -10px;
		border-left: 2px solid transparent;
	}
	nav a:hover {
		background: var(--hover);
		text-decoration: none;
	}
	nav a.active {
		color: var(--ink);
		font-weight: 500;
		border-left-color: var(--ink);
	}
	.foot {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.foot p {
		font-size: 11.5px;
		line-height: 1.5;
		margin: 0;
	}
	.gh {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 11.5px;
		color: var(--ink-2);
	}
	.gh:hover {
		color: var(--ink);
		text-decoration: none;
	}
	main {
		padding: 48px 56px;
		max-width: var(--maxw);
		width: 100%;
	}
	/* mobile: sidebar collapses to a sticky top bar with a hamburger dropdown */
	@media (max-width: 760px) {
		.shell {
			display: block;
		}
		aside {
			display: block;
			position: sticky;
			top: 0;
			z-index: 20;
			height: auto;
			overflow: visible;
			background: var(--bg);
			border-right: none;
			border-bottom: 1px solid var(--line);
			padding: 0;
			gap: 0;
		}
		.topbar {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 13px 18px;
		}
		.brand {
			flex-direction: row;
			align-items: center;
			gap: 9px;
		}
		.mark {
			font-size: 11px;
			padding: 3px 6px;
		}
		.title {
			display: none;
		}
		.title-m {
			display: block;
			font-size: 15px;
			font-weight: 600;
			letter-spacing: -0.02em;
			color: var(--ink);
		}
		.burger {
			display: flex;
			flex-direction: column;
			justify-content: center;
			gap: 4px;
			width: 40px;
			height: 40px;
			padding: 0;
			border: 1px solid var(--line-2);
			background: var(--bg);
		}
		.burger span {
			display: block;
			width: 18px;
			height: 1.5px;
			margin: 0 auto;
			background: var(--ink);
			transition: transform 0.18s, opacity 0.18s;
		}
		.burger.open span:nth-child(1) {
			transform: translateY(5.5px) rotate(45deg);
		}
		.burger.open span:nth-child(2) {
			opacity: 0;
		}
		.burger.open span:nth-child(3) {
			transform: translateY(-5.5px) rotate(-45deg);
		}
		.panel {
			display: none;
		}
		aside.open .panel {
			display: block;
			border-top: 1px solid var(--line);
			max-height: calc(100vh - 67px);
			overflow-y: auto;
		}
		nav {
			gap: 1px;
			padding: 10px 18px 14px;
		}
		.group-label {
			margin: 16px 0 4px;
		}
		nav a {
			font-size: 15px;
			padding: 11px 10px;
			margin: 0;
		}
		.foot {
			display: flex;
			margin-top: 0;
			padding: 14px 18px 20px;
			border-top: 1px solid var(--line);
		}
		main {
			padding: 26px 18px 48px;
		}
	}
</style>
