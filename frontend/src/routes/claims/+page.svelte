<script lang="ts">
	import { goto } from '$app/navigation';
	$effect(() => {
		goto('/report', { replaceState: true });
	});
</script>

<p class="muted">Redirecting to Report fraud…</p>
