<script>
    import { onMount, onDestroy } from 'svelte';
    import { marked } from 'marked';

    // Component Props
    let { 
        text = '', 
        speed: initialSpeed = 1.0 
    } = $props();

    // Internal component states
    let containerEl = $state(null);
    let isSpeaking = $state(false);
    let isPaused = $state(false);
    let currentWordIndex = $state(-1);
    let speed = $state(initialSpeed);

    let htmlContentWithSpans = $state('');
    let cleanText = $state('');
    let words = []; // Array of { word: string, start: number, end: number }

    let speechSynth;
    let currentUtterance = null;

    // Process markdown source text into individual text nodes wrapped by tts-word spans
    function parseAndPrepareHTML(markdownText) {
        if (!markdownText) {
            htmlContentWithSpans = '';
            cleanText = '';
            words = [];
            currentWordIndex = -1;
            return;
        }
        
        // Compile markdown to standard HTML structure
        let rawHtml = '';
        try {
            rawHtml = marked.parse(markdownText);
        } catch (e) {
            rawHtml = markdownText;
        }
        
        if (typeof window === 'undefined') {
            htmlContentWithSpans = rawHtml;
            return;
        }
        
        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml, 'text/html');
        cleanText = doc.body.textContent.trim();
        
        // Build the words array with precise character indices in cleanText
        words = [];
        const regex = /\S+/g;
        let match;
        while ((match = regex.exec(cleanText)) !== null) {
            words.push({
                word: match[0],
                start: match.index,
                end: match.index + match[0].length
            });
        }
        
        // Split doc.body children into staggered sections for a visual reveal experience
        const sections = [];
        let currentSection = doc.createElement('div');
        currentSection.className = 'staggered-section';
        currentSection.style.setProperty('--delay', '0ms');
        
        let secIdx = 0;
        Array.from(doc.body.childNodes).forEach(node => {
            if (node.nodeType === 1 && (node.tagName === 'H2' || node.tagName === 'H3' || node.tagName === 'H4')) {
                if (currentSection.childNodes.length > 0) {
                    sections.push(currentSection);
                }
                currentSection = doc.createElement('div');
                currentSection.className = 'staggered-section';
                secIdx++;
                currentSection.style.setProperty('--delay', `${secIdx * 150}ms`);
            }
            currentSection.appendChild(node.cloneNode(true));
        });
        if (currentSection.childNodes.length > 0) {
            sections.push(currentSection);
        }
        
        // Re-inject the staggered sections into the body
        doc.body.innerHTML = '';
        sections.forEach(sec => doc.body.appendChild(sec));
        
        let wordIdx = 0;
        
        function walk(node) {
            if (node.nodeType === 3) { // TEXT_NODE
                const val = node.nodeValue;
                const splitWords = val.split(/(\s+)/);
                const parent = node.parentNode;
                
                splitWords.forEach(part => {
                    if (part.trim() === '') {
                        parent.insertBefore(document.createTextNode(part), node);
                    } else {
                        const span = document.createElement('span');
                        span.className = 'tts-word pending-word';
                        span.setAttribute('data-word-idx', wordIdx.toString());
                        span.textContent = part;
                        parent.insertBefore(span, node);
                        wordIdx++;
                    }
                });
                parent.removeChild(node);
            } else {
                const children = Array.from(node.childNodes);
                children.forEach(walk);
            }
        }
        
        walk(doc.body);
        htmlContentWithSpans = doc.body.innerHTML;
    }

    // Maps charIndex from boundary events to the corresponding word index
    function getWordIndexForCharIndex(charIndex) {
        for (let i = 0; i < words.length; i++) {
            if (charIndex >= words[i].start && charIndex < words[i].end) {
                return i;
            }
        }
        for (let i = 0; i < words.length; i++) {
            if (words[i].start >= charIndex) {
                return i;
            }
        }
        return words.length - 1;
    }

    // Speech controllers
    function playSpeech() {
        if (!speechSynth || !cleanText) return;
        speechSynth.cancel();
        
        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        // Use browser default voice automatically to prevent multilingual failures
        utterance.voice = null;
        
        // Set speech speed rate
        utterance.rate = speed;
        
        utterance.onstart = () => {
            isSpeaking = true;
            isPaused = false;
        };
        
        // Sync spoken index with boundary charIndexes
        utterance.onboundary = (event) => {
            if (event.name === 'word') {
                const charIndex = event.charIndex;
                const wordIndex = getWordIndexForCharIndex(charIndex);
                
                requestAnimationFrame(() => {
                    currentWordIndex = wordIndex;
                });
            }
        };
        
        utterance.onend = () => {
            cleanupSpeech();
        };
        
        utterance.onerror = () => {
            cleanupSpeech();
        };
        
        currentUtterance = utterance;
        isSpeaking = true;
        isPaused = false;
        speechSynth.speak(utterance);
    }

    function pauseSpeech() {
        if (!speechSynth || !isSpeaking) return;
        speechSynth.pause();
        isPaused = true;
    }

    function resumeSpeech() {
        if (!speechSynth || !isSpeaking) return;
        speechSynth.resume();
        isPaused = false;
    }

    function stopSpeech() {
        if (!speechSynth) return;
        speechSynth.cancel();
        cleanupSpeech();
    }

    function cleanupSpeech() {
        isSpeaking = false;
        isPaused = false;
        currentWordIndex = -1;
        currentUtterance = null;
    }

    // Svelte 5 Reactive Effects
    $effect(() => {
        parseAndPrepareHTML(text);
    });

    // Scoped DOM class updater bound to currentWordIndex changes
    $effect(() => {
        if (containerEl && typeof document !== 'undefined') {
            const wordsElements = containerEl.querySelectorAll('.tts-word');
            wordsElements.forEach(el => {
                const idx = parseInt(el.getAttribute('data-word-idx') || '-1', 10);
                if (idx === currentWordIndex) {
                    el.className = 'tts-word current-word';
                    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else if (idx < currentWordIndex) {
                    el.className = 'tts-word spoken-word';
                } else {
                    el.className = 'tts-word pending-word';
                }
            });
        }
    });

    onMount(() => {
        if (typeof window !== 'undefined') {
            speechSynth = window.speechSynthesis;
        }
    });

    onDestroy(() => {
        if (speechSynth) {
            speechSynth.cancel();
        }
    });
</script>

<div class="reading-highlighter-panel">
    <!-- Header TTS Controllers -->
    <div class="highlighter-controls">
        <!-- Audio Trigger Buttons -->
        <div class="audio-buttons">
            {#if !isSpeaking}
                <button 
                    class="ctrl-btn play-btn" 
                    onclick={playSpeech} 
                    aria-label="Start reading content aloud"
                    type="button"
                >
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                    <span>Play Read-Aloud</span>
                </button>
            {:else}
                <div class="active-ctrl-group">
                    {#if !isPaused}
                        <button 
                            class="ctrl-btn pause-btn" 
                            onclick={pauseSpeech} 
                            aria-label="Pause narration"
                            type="button"
                        >
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                            <span>Pause</span>
                        </button>
                    {:else}
                        <button 
                            class="ctrl-btn resume-btn" 
                            onclick={resumeSpeech} 
                            aria-label="Resume narration"
                            type="button"
                        >
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>
                            <span>Resume</span>
                        </button>
                    {/if}
                    <button 
                        class="ctrl-btn stop-btn" 
                        onclick={stopSpeech} 
                        aria-label="Stop narration"
                        type="button"
                    >
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6 6h12v12H6z"/></svg>
                        <span>Stop</span>
                    </button>
                </div>
            {/if}
        </div>

        <!-- Telemetry Configurations -->
        <div class="telemetry-settings">
            <!-- Reading rate speed slider -->
            <div class="setting-item">
                <div class="val-header">
                    <label for="speed-slider">Narration Speed</label>
                    <span class="speed-val">{speed.toFixed(2)}x</span>
                </div>
                <input 
                    id="speed-slider"
                    type="range" 
                    min="0.5" 
                    max="2.0" 
                    step="0.1" 
                    bind:value={speed}
                    oninput={() => {
                        if (isSpeaking && !isPaused && currentUtterance) {
                            // Trigger speech restart at new rate speed dynamically
                            playSpeech();
                        }
                    }}
                    aria-label="Adjust speaking speed"
                />
            </div>
        </div>
    </div>

    <!-- Dynamic Highlights Viewport -->
    <div bind:this={containerEl} class="highlighter-viewport markdown-content">
        {@html htmlContentWithSpans}
    </div>
</div>

<style>
    .reading-highlighter-panel {
        display: flex;
        flex-direction: column;
        width: 100%;
        gap: 1.25rem;
    }

    /* Controls Bar styling */
    .highlighter-controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
        background: rgba(11, 15, 27, 0.4);
        border: 1px solid var(--border);
        padding: 1rem 1.25rem;
        border-radius: 16px;
        backdrop-filter: blur(10px);
    }

    .audio-buttons {
        display: flex;
        align-items: center;
    }

    .active-ctrl-group {
        display: flex;
        gap: 0.5rem;
    }

    .ctrl-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        border: none;
        padding: 10px 16px;
        border-radius: 10px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        color: white;
    }

    .play-btn {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        box-shadow: var(--glow-indigo);
    }

    .play-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.35);
    }

    .play-btn:active {
        transform: translateY(1px);
    }

    .pause-btn, .resume-btn {
        background: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.25);
        color: var(--secondary);
    }

    .pause-btn:hover, .resume-btn:hover {
        background: rgba(6, 182, 212, 0.18);
        box-shadow: var(--glow-cyan);
        transform: translateY(-2px);
    }

    .pause-btn:active, .resume-btn:active {
        transform: translateY(1px);
    }

    .stop-btn {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        color: #f87171;
    }

    .stop-btn:hover {
        background: rgba(239, 68, 68, 0.18);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.2);
        transform: translateY(-2px);
    }

    .stop-btn:active {
        transform: translateY(1px);
    }

    .telemetry-settings {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        align-items: center;
    }

    @media (max-width: 600px) {
        .highlighter-controls {
            flex-direction: column;
            align-items: stretch;
        }
        .telemetry-settings {
            flex-direction: column;
            align-items: stretch;
            gap: 1rem;
        }
    }

    .setting-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 180px;
    }

    .setting-item label {
        font-size: 0.72rem;
        color: var(--text-muted);
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .val-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .speed-val {
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--accent);
    }

    .setting-item input[type="range"] {
        accent-color: var(--accent);
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        outline: none;
    }

    /* Viewport text spans styling */
    .highlighter-viewport {
        background: rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.8rem;
        font-size: 1.05rem;
        line-height: 1.6;
    }

    /* Staggered animation layout */
    :global(.staggered-section) {
        opacity: 0;
        transform: translateY(12px);
        animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: var(--delay, 0ms);
        margin-bottom: 1.5rem;
    }

    :global(.staggered-section:last-child) {
        margin-bottom: 0;
    }

    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* TTS word highlights CSS properties - Apple books immersive reading theme */
    :global(.tts-word) {
        display: inline-block;
        transition: color 0.22s ease, transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), text-shadow 0.22s ease, opacity 0.22s ease;
        border-radius: 4px;
        padding: 0 2px;
        position: relative;
    }

    :global(.tts-word.current-word) {
        color: #00f0ff !important; /* Bright cyan */
        transform: scale(1.08) translateY(-1px);
        text-shadow: 0 0 12px rgba(0, 240, 255, 0.8), 0 0 20px rgba(0, 240, 255, 0.4);
        opacity: 1 !important;
        font-weight: 600;
        z-index: 2;
    }

    :global(.tts-word.current-word::after) {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, #00f0ff, #10b981);
        border-radius: 2px;
        animation: active-underline 0.3s ease-out forwards;
    }

    @keyframes active-underline {
        0% { width: 0; left: 50%; }
        100% { width: 100%; left: 0; }
    }

    :global(.tts-word.spoken-word) {
        color: #a7f3d0 !important; /* Emerald green tint */
        opacity: 0.6;
    }

    :global(.tts-word.pending-word) {
        color: var(--text-primary);
        opacity: 1;
    }
</style>
