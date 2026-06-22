<script>
    import ReadingHighlighter from './ReadingHighlighter.svelte';

    let { mcqs = [], targetObject = '' } = $props();

    let selectedAnswers = $state({});
    let isSubmitted = $state(false);
    let score = $state(0);
    let confettiElements = $state([]);

    function triggerConfetti() {
        const colors = ['#22c55e', '#16a34a', '#86efac', '#f59e0b', '#f3f4f6', '#9ca3af'];
        const tempConfetti = [];
        for (let i = 0; i < 80; i++) {
            tempConfetti.push({
                id: i,
                x: Math.random() * 100,
                y: -10 - Math.random() * 20,
                size: 6 + Math.random() * 8,
                color: colors[Math.floor(Math.random() * colors.length)],
                delay: Math.random() * 1.2,
                duration: 2 + Math.random() * 2,
                angle: Math.random() * 360,
                spinSpeed: 0.5 + Math.random() * 1.5
            });
        }
        confettiElements = tempConfetti;
        setTimeout(() => {
            confettiElements = [];
        }, 4500);
    }

    let answeredCount = $derived(Object.keys(selectedAnswers).length);

    let feedbackText = $derived(
        score === mcqs.length
            ? `Perfect score recorded. You have fully mastered the ${targetObject} study matrix.`
            : score >= 3
                ? `Strong diagnostic results. Minor details remain to reach catalog mastery.`
                : `Concept threshold not reached. We recommend reviewing study sheets and re-scanning.`
    );

    $effect(() => {
        if (mcqs) {
            selectedAnswers = {};
            isSubmitted = false;
            score = 0;
        }
    });

    function selectOption(qIdx, option) {
        if (isSubmitted) return;
        selectedAnswers[qIdx] = option;
    }

    // Robust correct option matching logic supporting index, prefix (A.), or full-text values
    function checkOptionCorrect(mcq, option, optIdx) {
        const answerStr = mcq.answer.trim();

        // Case 1: Answer is a single index letter (A, B, C, D)
        if (/^[A-D]$/i.test(answerStr)) {
            const correctLetterIdx = answerStr.toUpperCase().charCodeAt(0) - 65;
            return optIdx === correctLetterIdx;
        }

        // Case 2: Answer is full text (with/without index prefixes)
        const cleanOption = option.replace(/^[A-D]\.\s*/i, '').trim().toLowerCase();
        const cleanAnswer = answerStr.replace(/^[A-D]\.\s*/i, '').trim().toLowerCase();

        return cleanOption === cleanAnswer || option.trim().toLowerCase() === answerStr.toLowerCase();
    }

    function isUserAnswerCorrect(mcq, selected) {
        if (!selected) return false;
        const selectedIdx = mcq.options.indexOf(selected);
        if (selectedIdx === -1) return false;
        return checkOptionCorrect(mcq, selected, selectedIdx);
    }

    function submitQuiz() {
        if (isSubmitted) return;

        let tempScore = 0;
        mcqs.forEach((mcq, idx) => {
            let selected = selectedAnswers[idx];
            if (!selected) return;

            const selectedIdx = mcq.options.indexOf(selected);
            if (selectedIdx !== -1 && checkOptionCorrect(mcq, selected, selectedIdx)) {
                tempScore++;
            }
        });

        score = tempScore;
        isSubmitted = true;

        if (score === mcqs.length && mcqs.length > 0) {
            if (typeof window !== 'undefined') {
                const count = localStorage.getItem('visionai_perfect_quiz_count') || '0';
                localStorage.setItem('visionai_perfect_quiz_count', (parseInt(count, 10) + 1).toString());
            }
            triggerConfetti();
        }
    }

    function resetQuiz() {
        selectedAnswers = {};
        isSubmitted = false;
        score = 0;
    }
</script>

{#if mcqs && mcqs.length > 0}
    <div class="quiz-container">
        <h3 class="quiz-heading">🎓 Diagnostic Examination: {targetObject}</h3>

        <!-- Progression Indicator -->
        <div class="quiz-progress-section">
            <div class="progress-labels">
                <span class="lbl-main">Inference Check progress</span>
                <span class="lbl-val">{answeredCount} of {mcqs.length} answered</span>
            </div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill" style="width: {(answeredCount / mcqs.length) * 100}%"></div>
            </div>
        </div>

        {#each mcqs as mcq, idx}
            {@const userCorrect = isUserAnswerCorrect(mcq, selectedAnswers[idx])}
            <div class="question-card" class:correct-card={isSubmitted && userCorrect} class:incorrect-card={isSubmitted && !userCorrect}>
                <div class="q-number">Specimen Question {idx + 1}</div>
                <div class="q-text">{mcq.question}</div>

                <div class="options-grid">
                    {#each mcq.options as option, optIdx}
                        {@const isSelected = selectedAnswers[idx] === option}
                        {@const isOptionCorrect = checkOptionCorrect(mcq, option, optIdx)}

                        <button
                            class="option-btn"
                            class:selected={isSelected}
                            class:correct={isSubmitted && isOptionCorrect}
                            class:incorrect={isSubmitted && isSelected && !isOptionCorrect}
                            onclick={() => selectOption(idx, option)}
                            disabled={isSubmitted}
                            type="button"
                        >
                            <span class="option-indicator"></span>
                            <span class="option-label">{option}</span>
                        </button>
                    {/each}
                </div>
            </div>
        {/each}

        <!-- Actions -->
        <div class="actions-row">
            {#if !isSubmitted}
                <button class="submit-btn" onclick={submitQuiz} disabled={answeredCount < mcqs.length}>
                    Submit Diagnostic Answers
                </button>
            {:else}
                <div class="results-banner">
                    <div class="score-radial" class:success={score >= 3} class:perfect={score === mcqs.length}>
                        <span class="score-num">{score} / {mcqs.length}</span>
                        <span class="score-pct">{Math.round((score / mcqs.length) * 100)}%</span>
                    </div>
                    <div class="results-text">
                        <div class="badge-row">
                            {#if score === mcqs.length}
                                <span class="badge perfect-badge">🏆 MASTERED</span>
                            {:else if score >= 3}
                                <span class="badge verified-badge">⚡ VERIFIED</span>
                            {:else}
                                <span class="badge practice-badge">⏳ PRACTICE RUN</span>
                            {/if}
                            <h4>Diagnostic Completed!</h4>
                        </div>
                        <div class="quiz-explanation-highlighter" style="margin-bottom: 0.75rem; width: 100%;">
                            <ReadingHighlighter text={feedbackText} />
                        </div>
                        <button class="reset-btn" onclick={resetQuiz}>Re-Run Diagnostic</button>
                    </div>
                </div>
            {/if}

            {#if confettiElements.length > 0}
                <div class="confetti-container">
                    {#each confettiElements as c (c.id)}
                        <div
                            class="confetti-piece"
                            style="
                                left: {c.x}%;
                                top: {c.y}px;
                                width: {c.size}px;
                                height: {c.size}px;
                                background-color: {c.color};
                                animation-delay: {c.delay}s;
                                animation-duration: {c.duration}s;
                                transform: rotate({c.angle}deg);
                                --spin-speed: {c.spinSpeed}s;
                            "
                        ></div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
{:else}
    <div class="no-quiz">No active specimen quiz. Select or scan a specimen to compile study diagnostics.</div>
{/if}

<style>
    .quiz-container {
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 1000px;
        margin: 1.5rem auto;
        gap: 1.5rem;
    }

    .quiz-heading {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 0.2rem;
        text-align: center;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Progression Track */
    .quiz-progress-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .progress-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
    }

    .progress-labels .lbl-main {
        color: var(--text-secondary);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .progress-labels .lbl-val {
        color: var(--secondary);
        font-weight: 700;
    }

    .progress-bar-track {
        height: 6px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 6px;
        overflow: hidden;
        width: 100%;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        border-radius: 6px;
        transition: width 0.4s ease;
    }

    /* Question Card Styling */
    .question-card {
        background: var(--bg-card);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.8rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .question-card:hover {
        border-color: rgba(255, 255, 255, 0.1);
        transform: translateY(-1px);
    }

    .question-card.correct-card {
        border-color: rgba(16, 185, 129, 0.2) !important;
        background: rgba(16, 185, 129, 0.02) !important;
        box-shadow: 0 0 25px rgba(16, 185, 129, 0.03) !important;
    }

    .question-card.incorrect-card {
        border-color: rgba(239, 68, 68, 0.2) !important;
        background: rgba(239, 68, 68, 0.02) !important;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.03) !important;
    }

    .q-number {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .q-text {
        font-size: 1.1rem;
        font-weight: 500;
        color: #f1f5f9;
        line-height: 1.4;
    }

    /* Options Styling */
    .options-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    @media (min-width: 600px) {
        .options-grid {
            grid-template-columns: 1fr 1fr;
        }
    }

    .option-btn {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 14px 18px;
        cursor: pointer;
        text-align: left;
        color: var(--text-secondary);
        font-size: 0.95rem;
        font-weight: 500;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
        box-sizing: border-box;
    }

    .option-btn:hover:not(:disabled) {
        background: rgba(34, 197, 94, 0.06);
        border-color: rgba(34, 197, 94, 0.3);
        color: #f1f5f9;
    }

    .option-btn.selected {
        background: rgba(34, 197, 94, 0.12);
        border-color: var(--primary);
        color: #f8fafc;
        box-shadow: var(--glow-surface);
    }

    .option-indicator {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: all 0.2s ease;
    }

    .option-btn.selected .option-indicator {
        border-color: var(--primary);
        background: var(--primary);
        box-shadow: 0 0 8px var(--primary);
    }

    /* Correct / Incorrect Option Coloring on Submission */
    .option-btn.correct {
        background: rgba(16, 185, 129, 0.1) !important;
        border-color: var(--accent) !important;
        color: #f8fafc !important;
        box-shadow: var(--glow-emerald) !important;
    }

    .option-btn.correct .option-indicator {
        border-color: var(--accent) !important;
        background: var(--accent) !important;
        box-shadow: 0 0 8px var(--accent);
    }

    .option-btn.incorrect {
        background: rgba(239, 68, 68, 0.1) !important;
        border-color: #ef4444 !important;
        color: #f8fafc !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.15) !important;
    }

    .option-btn.incorrect .option-indicator {
        border-color: #ef4444 !important;
        background: #ef4444 !important;
        box-shadow: 0 0 8px #ef4444;
    }

    /* Actions Row */
    .actions-row {
        display: flex;
        justify-content: center;
        width: 100%;
        margin-top: 1rem;
    }

    .submit-btn {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        border: none;
        color: white;
        padding: 14px 40px;
        border-radius: 14px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 8px 24px rgba(3, 7, 18, 0.22);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .submit-btn:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow:
            0 12px 30px rgba(3, 7, 18, 0.28),
            var(--glow-primary);
    }

    .submit-btn:disabled {
        opacity: 0.35;
        cursor: not-allowed;
        box-shadow: none;
    }

    /* Results Banner */
    .results-banner {
        width: 100%;
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 2rem;
        display: flex;
        align-items: center;
        gap: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    @media (max-width: 550px) {
        .results-banner {
            flex-direction: column;
            text-align: center;
            gap: 1.2rem;
        }
    }

    .score-radial {
        width: 110px;
        height: 110px;
        border-radius: 50%;
        border: 4px solid #ef4444;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        flex-shrink: 0;
        background: rgba(239, 68, 68, 0.02);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.05);
    }

    .score-radial.success {
        border-color: var(--secondary);
        background: rgba(34, 197, 94, 0.04);
        box-shadow: var(--glow-primary);
    }

    .score-radial.perfect {
        border-color: var(--accent);
        background: rgba(16, 185, 129, 0.02);
        box-shadow: var(--glow-emerald);
    }

    .score-num {
        font-size: 1.35rem;
        font-weight: 700;
        color: #f8fafc;
    }

    .score-pct {
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .results-text {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        align-items: flex-start;
        flex-grow: 1;
    }

    @media (max-width: 550px) {
        .results-text {
            align-items: center;
        }
    }

    .badge-row {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }

    .badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 6px;
        width: max-content;
        letter-spacing: 0.05em;
    }

    .perfect-badge {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid var(--accent);
        color: var(--accent);
    }

    .verified-badge {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid var(--secondary);
        color: var(--secondary);
    }

    .practice-badge {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: var(--text-secondary);
    }

    .results-text h4 {
        margin: 0.25rem 0 0 0;
        font-size: 1.25rem;
        font-weight: 700;
        color: #f1f5f9;
    }

    .reset-btn {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #f1f5f9;
        padding: 8px 20px;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        margin-top: 0.5rem;
        transition: all 0.2s ease;
    }

    .reset-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-1px);
    }

    .no-quiz {
        text-align: center;
        padding: 3rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.01);
        border: 1px dashed rgba(255, 255, 255, 0.08);
        border-radius: 16px;
    }
</style>
