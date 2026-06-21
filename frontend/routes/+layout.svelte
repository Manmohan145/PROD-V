<script>
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>VisionAI - Intelligent Object Recognition</title>
</svelte:head>

{@render children()}

