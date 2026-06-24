<script>
	import { ICONS } from '$lib/icons.js';

	let { name, size = 18, strokeWidth = 1.8, spin = false, class: className = '' } = $props();
</script>

<svg
	class="vi-icon {className}"
	class:vi-icon-spin={spin}
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	{@html ICONS[name] || ''}
</svg>

<style>
	.vi-icon {
		display: inline-block;
		vertical-align: -3px;
		flex-shrink: 0;
		transition: transform 0.2s ease;
	}

	.vi-icon-spin {
		animation: vi-icon-spin 1s linear infinite;
	}

	@keyframes vi-icon-spin {
		to { transform: rotate(360deg); }
	}
</style>
