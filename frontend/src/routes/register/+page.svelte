<script lang="ts">
	// Register search was merged into Provider check.
	import { goto } from '$app/navigation';
	$effect(() => {
		goto('/check', { replaceState: true });
	});
</script>

<p class="muted">Redirecting to Provider check…</p>
