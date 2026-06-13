<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Overview' },
		{ href: '/money', label: 'Fraud value' },
		{ href: '/phoenix', label: 'Banned & back' },
		{ href: '/claims', label: 'Claims lab' },
		{ href: '/dossiers', label: 'Case dossiers' },
		{ href: '/check', label: 'Provider check' },
		{ href: '/register', label: 'Register' },
		{ href: '/typologies', label: 'Typologies' },
		{ href: '/diff', label: 'Register diff' }
	];
	const current = $derived(page.url.pathname);
</script>

<div class="shell">
	<aside>
		<div class="brand">
			<div class="mark">NDIS</div>
			<div class="title">Provider Integrity<br />Observatory</div>
		</div>
		<nav>
			{#each nav as item}
				<a href={item.href} class:active={current === item.href}>{item.label}</a>
			{/each}
		</nav>
		<div class="foot">
			<p class="muted">Public data. Leads for verification, not allegations.</p>
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
	nav {
		display: flex;
		flex-direction: column;
		gap: 1px;
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
	main {
		padding: 48px 56px;
		max-width: var(--maxw);
		width: 100%;
	}
	@media (max-width: 760px) {
		.shell {
			grid-template-columns: 1fr;
		}
		aside {
			position: static;
			height: auto;
		}
		main {
			padding: 28px 22px;
		}
	}
</style>
