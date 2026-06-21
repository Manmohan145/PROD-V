<script>
    import ReadingHighlighter from './ReadingHighlighter.svelte';

    let { flashcards = [] } = $props();
    let activeIndex = $state(0);
    let isFlipped = $state(false);

    $effect(() => {
        // Reset flip state when card list or object changes
        if (flashcards) {
            isFlipped = false;
            activeIndex = 0;
        }
    });

    function handleFlip() {
        isFlipped = !isFlipped;
    }

    function nextCard() {
        isFlipped = false;
        setTimeout(() => {
            activeIndex = (activeIndex + 1) % flashcards.length;
        }, 150);
    }

    function prevCard() {
        isFlipped = false;
        setTimeout(() => {
            activeIndex = (activeIndex - 1 + flashcards.length) % flashcards.length;
        }, 150);
    }
</script>

{#if flashcards && flashcards.length > 0}
    <div class="deck-container">
        <!-- 3D Card Wrapper -->
        <div class="card-perspective" onclick={handleFlip} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && handleFlip()}>
            <div class="card-inner" class:flipped={isFlipped}>
                
                <!-- Card Front -->
                <div class="card-face card-front">
                    <div class="card-glow"></div>
                    <div class="card-badge front-badge">SPECIMEN QUESTION</div>
                    <div class="card-text">{flashcards[activeIndex].front}</div>
                    <div class="card-action-text">Click card to reveal catalog answer</div>
                </div>

                <!-- Card Back -->
                <div class="card-face card-back">
                    <div class="card-glow"></div>
                    <div class="card-badge back-badge">SPECIMEN ANSWER</div>
                    <div class="card-text" onclick={(e) => e.stopPropagation()} role="presentation">
                        <ReadingHighlighter text={flashcards[activeIndex].back} />
                    </div>
                    <div class="card-action-text">Click card to return to question</div>
                </div>

            </div>
        </div>

        <!-- Custom Pagination Dots -->
        <div class="deck-progress-dots">
            {#each flashcards as _, idx}
                <div class="progress-dot" class:active={idx === activeIndex}></div>
            {/each}
        </div>

        <!-- Controls -->
        <div class="controls-row">
            <button class="nav-btn" onclick={prevCard} aria-label="Previous card">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"></polyline></svg>
                <span>Prev</span>
            </button>
            <span class="card-counter">Specimen Card {activeIndex + 1} of {flashcards.length}</span>
            <button class="nav-btn" onclick={nextCard} aria-label="Next card">
                <span>Next</span>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
        </div>
    </div>
{:else}
    <div class="no-cards">No flashcards available. Select or scan a specimen to compile custom flashcards.</div>
{/if}

<style>
    .deck-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
        max-width: 700px;
        margin: 2rem auto;
        gap: 1rem;
    }

    /* 3D Card Styles */
    .card-perspective {
        perspective: 1000px;
        width: 100%;
        height: 350px;
        cursor: pointer;
        outline: none;
    }

    .card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        transform-style: preserve-3d;
    }

    .card-inner.flipped {
        transform: rotateY(180deg);
    }

    .card-face {
        position: absolute;
        width: 100%;
        height: 100%;
        backface-visibility: hidden;
        border-radius: 20px;
        padding: 2.5rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        overflow: hidden;
        box-sizing: border-box;
    }

    /* Front Card Styling */
    .card-front {
        background: var(--bg-card);
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 
            0 15px 35px rgba(0, 0, 0, 0.3), 
            inset 0 1px 1px rgba(255, 255, 255, 0.05),
            var(--glow-indigo);
        color: #f1f5f9;
    }

    /* Back Card Styling */
    .card-back {
        background: rgba(18, 20, 36, 0.85);
        border: 1px solid rgba(6, 182, 212, 0.15);
        box-shadow: 
            0 15px 35px rgba(0, 0, 0, 0.4), 
            inset 0 1px 1px rgba(6, 182, 212, 0.1),
            var(--glow-cyan);
        color: #f1f5f9;
        transform: rotateY(180deg);
    }

    .card-glow {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
    }

    .card-front .card-glow {
        background: radial-gradient(circle at 50% -20%, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0) 70%);
    }

    .card-back .card-glow {
        background: radial-gradient(circle at 50% -20%, rgba(6, 182, 212, 0.12) 0%, rgba(6, 182, 212, 0) 70%);
    }

    .card-badge {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        padding: 4px 10px;
        border-radius: 20px;
    }

    .front-badge {
        color: var(--accent);
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.15);
    }

    .back-badge {
        color: var(--secondary);
        background: rgba(6, 182, 212, 0.08);
        border: 1px solid rgba(6, 182, 212, 0.15);
    }

    .card-text {
        font-size: 1.25rem;
        font-weight: 500;
        line-height: 1.5;
        max-width: 100%;
        overflow-y: auto;
        padding: 0.5rem 0;
        color: #f8fafc;
    }

    .card-action-text {
        font-size: 0.72rem;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        text-transform: uppercase;
        animation: pulse-hud 2.5s infinite ease-in-out;
    }

    @keyframes pulse-hud {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }

    /* Progress Pagination Dots */
    .deck-progress-dots {
        display: flex;
        justify-content: center;
        gap: 6px;
        margin-top: 0.5rem;
    }

    .progress-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
        transition: all 0.25s ease;
    }

    .progress-dot.active {
        width: 18px;
        border-radius: 4px;
        background: var(--secondary);
        box-shadow: 0 0 6px var(--secondary);
    }

    /* Controls Styling */
    .controls-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-top: 0.5rem;
        gap: 1rem;
    }

    .nav-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: var(--text-secondary);
        padding: 10px 18px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .nav-btn:hover {
        background: rgba(99, 102, 241, 0.05);
        border-color: rgba(99, 102, 241, 0.2);
        color: #f8fafc;
        transform: translateY(-1px);
    }

    .card-counter {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .no-cards {
        text-align: center;
        padding: 3rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.01);
        border: 1px dashed rgba(255, 255, 255, 0.08);
        border-radius: 16px;
    }

    .card-text :global(.highlighter-viewport) {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        overflow-y: auto;
        max-height: 120px;
        width: 100%;
        font-size: 1.15rem;
        line-height: 1.45;
        text-align: center;
    }

    .card-text :global(.highlighter-controls) {
        background: rgba(255, 255, 255, 0.03) !important;
        padding: 6px 12px !important;
        border-radius: 10px !important;
        margin-bottom: 0.5rem;
        width: 100%;
        box-sizing: border-box;
    }
</style>
