<script lang="ts">
	let { kicker, title, lede }: { kicker?: string; title: string; lede?: string } = $props();
</script>

<header>
	{#if kicker}<div class="label">{kicker}</div>{/if}
	<h1>{title}</h1>
	{#if lede}<p class="lede soft">{lede}</p>{/if}
</header>

<style>
	header {
		margin-bottom: 36px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		max-width: 720px;
	}
	.lede {
		font-size: 15px;
		line-height: 1.55;
		margin: 0;
	}
</style>
