<script>
    import { onMount } from 'svelte';
    let bubbles = $state([]);

    onMount(() => {
        bubbles = Array.from({ length: 25 }, (_, i) => ({
            id: i,
            size: Math.random() * 90 + 20,       // 20px to 110px
            left: Math.random() * 100,           // 0% to 100%
            delay: Math.random() * 12,           // 0s to 12s
            duration: Math.random() * 20 + 15,   // 15s to 35s
            opacity: Math.random() * 0.18 + 0.05 // 5% to 23% opacity
        }));
    });
</script>

<div class="bubbles-container">
    {#each bubbles as bubble (bubble.id)}
        <div 
            class="bubble" 
            style:width="{bubble.size}px"
            style:height="{bubble.size}px"
            style:left="{bubble.left}%"
            style:animation-delay="{bubble.delay}s"
            style:animation-duration="{bubble.duration}s"
            style:opacity={bubble.opacity}
        ></div>
    {/each}
</div>

<style>
    .bubbles-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        z-index: 0;
        pointer-events: none;
        background: radial-gradient(circle at 50% 50%, #0a0f1d 0%, #04060b 100%);
    }

    .bubble {
        position: absolute;
        bottom: -150px;
        background: radial-gradient(
            circle at 35% 35%, 
            rgba(255, 255, 255, 0.4) 0%, 
            rgba(236, 72, 153, 0.1) 40%, 
            rgba(6, 182, 212, 0.05) 80%, 
            rgba(255, 255, 255, 0) 100%
        );
        border-radius: 50%;
        box-shadow: 
            0 8px 32px 0 rgba(0, 0, 0, 0.2), 
            inset 0 2px 6px rgba(255, 255, 255, 0.2), 
            0 0 15px rgba(6, 182, 212, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
        animation: float-up infinite linear;
    }

    @keyframes float-up {
        0% {
            transform: translateY(0) scale(1) translateX(0);
        }
        33% {
            transform: translateY(-40vh) scale(1.05) translateX(30px);
        }
        66% {
            transform: translateY(-80vh) scale(0.95) translateX(-30px);
        }
        100% {
            transform: translateY(-130vh) scale(1) translateX(0);
        }
    }
</style>
