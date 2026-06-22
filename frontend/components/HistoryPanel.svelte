<script>
    import { onMount } from 'svelte';
    import { API_BASE } from '$lib/api.js';

    let { onInspect, onUpdateCount } = $props();

    let history = $state([]);
    let loading = $state(true);
    let errorMsg = $state('');

    async function fetchHistory() {
        loading = true;
        errorMsg = '';
        try {
            const res = await fetch(`${API_BASE}/api/history`);
            if (!res.ok) throw new Error('Failed to fetch scan history');
            history = await res.json();
            if (onUpdateCount) onUpdateCount(history.length);
        } catch (err) {
            console.error(err);
            errorMsg = err.message || 'Could not connect to API server';
        } finally {
            loading = false;
        }
    }

    async function deleteRecord(id) {
        try {
            const res = await fetch(`${API_BASE}/api/history/${id}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete record');
            // Remove locally
            history = history.filter(item => item.id !== id);
            if (onUpdateCount) onUpdateCount(history.length);
        } catch (err) {
            alert(err.message);
        }
    }

    async function clearAll() {
        if (!confirm('Are you sure you want to permanently clear all scan history?')) return;
        try {
            const res = await fetch(`${API_BASE}/api/history/clear`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error('Failed to clear history');
            history = [];
            if (onUpdateCount) onUpdateCount(history.length);
        } catch (err) {
            alert(err.message);
        }
    }

    onMount(() => {
        fetchHistory();
    });
</script>

<div class="history-container">
    <div class="header-row">
        <h3>⏳ SQLite Scan History</h3>
        {#if history.length > 0}
            <button class="clear-btn" onclick={clearAll}>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                Clear History
            </button>
        {/if}
    </div>

    {#if loading}
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Retrieving archived scans from local database...</p>
        </div>
    {:else if errorMsg}
        <div class="error-state">
            <p>{errorMsg}</p>
            <button class="retry-btn" onclick={fetchHistory}>Retry Connection</button>
        </div>
    {:else if history.length === 0}
        <div class="empty-state">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="var(--primary)" stroke-width="1.5" style="filter: drop-shadow(0 6px 8px rgba(3, 7, 18, 0.28)); margin-bottom: 1.5rem;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <p>Your local scan history archive is currently empty.</p>
            <span>Once you capture or upload specimens, their diagnostic history will be recorded here.</span>
        </div>
    {:else}
        <div class="history-list">
            {#each history as item (item.id)}
                <div class="history-card">
                    <!-- Thumbnail -->
                    <div class="thumb-container">
                        {#if item.thumbnail}
                            <img src={item.thumbnail} alt={item.object_name} />
                        {:else}
                            <div class="no-thumb">No Image</div>
                        {/if}
                    </div>

                    <!-- Details -->
                    <div class="details-container">
                        <div class="object-title">{item.object_name}</div>
                        <div class="meta-row">
                            <span class="conf-badge">
                                🎯 {Math.round(item.confidence * 100)}% Match
                            </span>
                            <span class="time-stamp">
                                📅 {item.timestamp}
                            </span>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="actions-container">
                        <button class="action-btn inspect-btn" onclick={() => onInspect(item.object_name, item.confidence)}>
                            Inspect
                        </button>
                        <button class="action-btn delete-btn" onclick={() => deleteRecord(item.id)} aria-label="Delete record">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .history-container {
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 800px;
        margin: 1rem auto;
        gap: 1.2rem;
    }

    .header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 0.8rem;
    }

    .header-row h3 {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 700;
        color: #f8fafc;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .clear-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #f87171;
        padding: 8px 14px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .clear-btn:hover {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.35);
        transform: translateY(-1px);
    }

    /* List Layout */
    .history-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .history-card {
        display: flex;
        align-items: center;
        background: var(--bg-card);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1rem;
        gap: 1.2rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .history-card:hover {
        border-color: rgba(255, 255, 255, 0.12);
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    }

    /* Thumbnail Styles */
    .thumb-container {
        width: 100px;
        height: 70px;
        border-radius: 10px;
        overflow: hidden;
        background: #0f172a;
        flex-shrink: 0;
        border: 1px solid rgba(255, 255, 255, 0.05);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .thumb-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .no-thumb {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
    }

    /* Details Styles */
    .details-container {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        flex-grow: 1;
    }

    .object-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f1f5f9;
    }

    .meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: center;
    }

    .conf-badge {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--accent);
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.22);
        padding: 2px 8px;
        border-radius: 6px;
    }

    .time-stamp {
        font-size: 0.8rem;
        color: #64748b;
    }

    /* Actions Styles */
    .actions-container {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .inspect-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f1f5f9;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 8px 18px;
        border-radius: 10px;
    }

    .inspect-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.2);
        transform: translateY(-1px);
    }

    .delete-btn {
        background: transparent;
        border: none;
        color: #64748b;
        width: 36px;
        height: 36px;
        border-radius: 10px;
    }

    .delete-btn:hover {
        background: rgba(239, 68, 68, 0.08);
        color: #ef4444;
    }

    /* States Styles */
    .loading-state, .error-state, .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        text-align: center;
        background: rgba(21, 30, 51, 0.3);
        border: 1px dashed rgba(255, 255, 255, 0.08);
        border-radius: 20px;
    }

    .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid rgba(34, 197, 94, 0.1);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 1s infinite linear;
        margin-bottom: 1rem;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loading-state p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }

    .error-state p {
        color: #f87171;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }

    .retry-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f8fafc;
        padding: 8px 20px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 0.85rem;
    }

    .empty-state svg {
        color: #475569;
        margin-bottom: 1rem;
    }

    .empty-state p {
        color: #94a3b8;
        font-size: 1.15rem;
        font-weight: 500;
        margin: 0 0 0.25rem 0;
    }

    .empty-state span {
        color: #64748b;
        font-size: 0.85rem;
    }
</style>
