<script lang="ts">
	let { title, lede }: { title: string; lede?: string } = $props();
</script>

<header>
	<h1>{title}</h1>
	{#if lede}<p class="lede muted">{lede}</p>{/if}
</header>

<style>
	header {
		margin-bottom: 40px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		max-width: 640px;
	}
	.lede {
		font-size: 14px;
		line-height: 1.5;
		margin: 0;
	}
</style>
