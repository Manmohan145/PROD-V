<script>
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<meta name="theme-color" content="#111827" />
	<meta name="description" content="VisionAI Edge — AI research platform for vision, OCR, learning, and generative image workflows." />
	<title>VisionAI Edge — AI Research Platform</title>
</svelte:head>

{@render children()}
