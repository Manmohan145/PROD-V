<script>
    import { onMount, onDestroy } from 'svelte';
    import FlashcardDeck from '$components/FlashcardDeck.svelte';
    import QuizComponent from '$components/QuizComponent.svelte';
    import HistoryPanel from '$components/HistoryPanel.svelte';
    import ReadingHighlighter from '$components/ReadingHighlighter.svelte';
    import { marked } from 'marked';

    // Global App States
    let activeTab = $state('📸 Image Scanner');
    let visionEngine = $state('classification'); // 'classification' or 'detection'
    let confidenceThreshold = $state(0.25);
    let enableDemoMode = $state(false);
    let systemStatus = $state({ ollama_active: false, ollama_model: 'offline' });
    let statusChecking = $state(true);

    // Analysis tab states
    let uploadFile = $state(null);
    let isAnalyzing = $state(false);
    let analysisResult = $state(null);
    let analysisError = $state('');
    let selectedExploreLabel = $state('');
    let exploreResult = $state(null);
    let exploreLoading = $state(false);
    
    // Chat States
    let chatMessageInput = $state('');
    let chatHistory = $state([]); // array of {role, content}
    let chatLoading = $state(false);

    // Search tab states
    let searchQuery = $state('');
    let searchLoading = $state(false);
    let searchResult = $state(null);
    let searchError = $state('');

    // Learning Tab States
    let learningTarget = $state('Tiger');
    let learningLoading = $state(false);
    let learningData = $state(null);
    let learningError = $state('');

    // Futuristic Instrument HUD states
    let operatorGreeting = $state('System initialized.');
    let activeFact = $state('Operator manual loaded.');
    let studyStreak = $state(0);
    let totalSpecimensCount = $state(0);
    let uploadPreviewUrl = $state('');
    let visibleConfidence = $state({});
    let scanStep = $state(0); // 0 = idle/scanning, 1 = detection complete, 2 = confidence animating, 3 = knowledge loading, 4 = facts rendering, 5 = learning ready

    // OCR Tab States
    let ocrFile = $state(null);
    let ocrLoading = $state(false);
    let ocrResult = $state(null);
    let ocrError = $state('');

    // Comparison Tab States
    let compareA = $state('Tiger');
    let compareB = $state('Lion');
    let compareLoading = $state(false);
    let compareResult = $state(null);
    let compareError = $state('');

    // Webcam capturing elements
    let videoElement = $state();
    let webcamStream = $state();
    let isWebcamActive = $state(false);



    // Check Ollama and server status
    async function checkServerStatus() {
        statusChecking = true;
        try {
            const res = await fetch('http://127.0.0.1:8000/api/status');
            if (res.ok) {
                const data = await res.json();
                systemStatus = data;
            } else {
                systemStatus = { ollama_active: false, ollama_model: 'offline' };
            }
        } catch (err) {
            console.error('Server offline:', err);
            systemStatus = { ollama_active: false, ollama_model: 'offline' };
        } finally {
            statusChecking = false;
        }
    }



    // Note: Removed the pre-emptive /api/analyze ping effect. The backend dynamically switches 
    // the vision engine mode during the actual analyze requests.

    const scienceFacts = [
        "Octopuses possess three hearts, nine brains, and cobalt-blue blood.",
        "Solar photons take exactly 8 minutes and 20 seconds to transit from the Sun to Earth.",
        "Quantum entanglement allows states to influence each other instantaneously across any distance.",
        "A single teaspoon of a neutron star would weigh approximately 6 billion tons on Earth.",
        "Water can boil and freeze simultaneously at its thermodynamic 'triple point'.",
        "Venus rotates clockwise on its axis, unique among major Solar system planets.",
        "The focal rate of the human crystalline lens excels faster than advanced optical camera glass.",
        "Sonic compression waves propagate four times faster through liquid water than atmosphere."
    ];

    function initStreakSystem() {
        if (typeof window === 'undefined') return;
        const todayStr = new Date().toISOString().split('T')[0];
        const storedStreak = localStorage.getItem('visionai_streak_count');
        const storedDate = localStorage.getItem('visionai_last_active_date');
        
        let streak = storedStreak ? parseInt(storedStreak, 10) : 0;
        
        if (!storedDate) {
            streak = 1;
            localStorage.setItem('visionai_streak_count', '1');
            localStorage.setItem('visionai_last_active_date', todayStr);
        } else {
            const lastDate = new Date(storedDate);
            const todayDate = new Date(todayStr);
            const diffTime = Math.abs(todayDate - lastDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                streak += 1;
                localStorage.setItem('visionai_streak_count', streak.toString());
                localStorage.setItem('visionai_last_active_date', todayStr);
            } else if (diffDays > 1) {
                streak = 1;
                localStorage.setItem('visionai_streak_count', '1');
                localStorage.setItem('visionai_last_active_date', todayStr);
            }
        }
        studyStreak = streak;
    }

    function getOperatorGreeting() {
        const hour = new Date().getHours();
        let prefix = 'Good morning';
        if (hour >= 12 && hour < 17) prefix = 'Good afternoon';
        else if (hour >= 17 && hour < 22) prefix = 'Good evening';
        else if (hour >= 22 || hour < 5) prefix = 'Good night';
        
        const subtexts = [
            "Today is a great day to decode the physical world.",
            "Visual diagnostics are ready. Select a target.",
            "All offline knowledge engines are nominal.",
            "Curriculum compilers are primed for scanning.",
            "Ready to explore new concepts."
        ];
        const sub = subtexts[new Date().getDate() % subtexts.length];
        return `${prefix}, Operator. ${sub}`;
    }

    async function loadSpecimenCount() {
        try {
            const res = await fetch('http://127.0.0.1:8000/api/history');
            if (res.ok) {
                const history = await res.json();
                totalSpecimensCount = history.length;
            }
        } catch (e) {
            console.warn("Failed to fetch specimen logs count:", e);
        }
    }

    onMount(() => {
        checkServerStatus();
        initStreakSystem();
        loadSpecimenCount();
        
        operatorGreeting = getOperatorGreeting();
        activeFact = scienceFacts[Math.floor(Math.random() * scienceFacts.length)];
        
        const statusInterval = setInterval(checkServerStatus, 10000);
        const factInterval = setInterval(() => {
            activeFact = scienceFacts[Math.floor(Math.random() * scienceFacts.length)];
        }, 15000);
        
        return () => {
            clearInterval(statusInterval);
            clearInterval(factInterval);
            stopWebcam();
        };
    });

    onDestroy(() => {
        stopWebcam();
    });

    // ------------------------------------------------
    // API Call Pipelines
    // ------------------------------------------------

    // 1. Image Upload & Analyze API
    async function handleImageUpload(fileObj) {
        if (!fileObj) return;
        isAnalyzing = true;
        analysisError = '';
        analysisResult = null;
        selectedExploreLabel = '';
        exploreResult = null;
        chatHistory = [];
        scanStep = 0;
        
        // Generate a local preview URL for progressive scanning feed visual representation
        uploadPreviewUrl = URL.createObjectURL(fileObj);
        
        const formData = new FormData();
        formData.append('file', fileObj);
        formData.append('engine_mode', visionEngine);
        formData.append('confidence_threshold', confidenceThreshold.toString());

        try {
            const res = await fetch('http://127.0.0.1:8000/api/analyze', {
                method: 'POST',
                body: formData
            });
            
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Inference call failed');
            }
            
            analysisResult = await res.json();
            
            // Step 1: Detection Complete
            scanStep = 1;
            
            // Initialize progress bars at 0
            visibleConfidence = {};
            if (analysisResult.detections) {
                analysisResult.detections.forEach(det => {
                    visibleConfidence[det.label] = 0;
                });
            }
            
            // Refresh counts
            loadSpecimenCount();
            
            // After 600ms, go to Step 2: Confidence Animates
            setTimeout(() => {
                scanStep = 2;
                if (analysisResult && analysisResult.detections) {
                    analysisResult.detections.forEach(det => {
                        visibleConfidence[det.label] = det.confidence;
                    });
                }
                
                // After 1000ms (to let confidence bar fill animation show), go to Step 3: Knowledge Loading
                setTimeout(async () => {
                    if (analysisResult.top_label) {
                        selectedExploreLabel = analysisResult.top_label;
                        scanStep = 3; // Knowledge Loading
                        
                        await loadLabelDetails(selectedExploreLabel);
                        
                        // Once loaded, go to Step 4: Facts Appear Sequentially
                        scanStep = 4;
                        
                        // After 1500ms (let sequential reveal finish), go to Step 5: Learning Ready
                        setTimeout(() => {
                            scanStep = 5;
                        }, 1500);
                    }
                }, 1000);
            }, 600);
        } catch (err) {
            analysisError = err.message || 'Error executing vision detection';
        } finally {
            isAnalyzing = false;
        }
    }

    // Load detailed LLM analysis for a detected label
    async function loadLabelDetails(label) {
        exploreLoading = true;
        exploreResult = null;
        chatHistory = [
            { role: 'assistant', content: `Hi! I'm your local offline learning assistant. Ask me anything about the **${label}**.` }
        ];
        
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/search?q=${encodeURIComponent(label)}`);
            if (!res.ok) throw new Error('Could not fetch object profile');
            const data = await res.json();
            exploreResult = data.llm_info;
            
            // Set as learning target automatically for Learning tab convenience
            learningTarget = label;
        } catch (err) {
            console.error(err);
        } finally {
            exploreLoading = false;
        }
    }

    // Submit dialog chat query to Ollama
    async function sendChatMessage() {
        if (!chatMessageInput.trim() || chatLoading) return;
        
        const userMsg = { role: 'user', content: chatMessageInput.trim() };
        chatHistory = [...chatHistory, userMsg];
        chatMessageInput = '';
        chatLoading = true;

        try {
            const res = await fetch('http://127.0.0.1:8000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected_label: selectedExploreLabel,
                    messages: chatHistory
                })
            });
            
            if (!res.ok) throw new Error('Chat generation failed');
            const data = await res.json();
            
            chatHistory = [...chatHistory, { role: 'assistant', content: data.reply }];
        } catch (err) {
            chatHistory = [...chatHistory, { role: 'assistant', content: `⚠️ Error: ${err.message}` }];
        } finally {
            chatLoading = false;
        }
    }

    // 2. Search Object API
    async function executeSearch() {
        if (!searchQuery.trim()) return;
        searchLoading = true;
        searchError = '';
        searchResult = null;
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/search?q=${encodeURIComponent(searchQuery.trim())}`);
            if (!res.ok) throw new Error('Search failed');
            searchResult = await res.json();
        } catch (err) {
            searchError = err.message || 'Error occurred while loading object data';
        } finally {
            searchLoading = false;
        }
    }

    // 3. Learning Mode Curriculum API
    async function loadLearningCurriculum() {
        if (!learningTarget.trim()) return;
        learningLoading = true;
        learningError = '';
        learningData = null;
        try {
            const res = await fetch('http://127.0.0.1:8000/api/learn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_object: learningTarget.trim() })
            });
            if (!res.ok) throw new Error('Failed to generate study guide');
            const result = await res.json();
            learningData = result.data;
        } catch (err) {
            learningError = err.message || 'Error generating curriculum';
        } finally {
            learningLoading = false;
        }
    }

    // 4. OCR Document Summarizer API
    async function executeOCR() {
        if (!ocrFile) return;
        ocrLoading = true;
        ocrError = '';
        ocrResult = null;
        const formData = new FormData();
        formData.append('file', ocrFile);
        try {
            const res = await fetch('http://127.0.0.1:8000/api/ocr', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) throw new Error('OCR extraction failed');
            ocrResult = await res.json();
        } catch (err) {
            ocrError = err.message || 'Failed to process document text';
        } finally {
            ocrLoading = false;
        }
    }

    // 5. Compare Objects API
    async function executeComparison() {
        if (!compareA.trim() || !compareB.trim()) return;
        compareLoading = true;
        compareError = '';
        compareResult = null;
        try {
            const res = await fetch('http://127.0.0.1:8000/api/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ object_a: compareA.trim(), object_b: compareB.trim() })
            });
            if (!res.ok) throw new Error('Comparison failed');
            const data = await res.json();
            compareResult = data.comparison;
        } catch (err) {
            compareError = err.message || 'Failed to compare concepts';
        } finally {
            compareLoading = false;
        }
    }

    // 6. Webcam controllers
    async function startWebcam() {
        try {
            webcamStream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: 1280, height: 720, facingMode: 'environment' } 
            });
            if (videoElement) {
                videoElement.srcObject = webcamStream;
                videoElement.play();
                isWebcamActive = true;
            }
        } catch (err) {
            alert('Cannot access camera: ' + err.message);
        }
    }

    function stopWebcam() {
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcamStream = null;
        }
        isWebcamActive = false;
    }

    function captureSnapshot() {
        if (!videoElement) return;
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth || 640;
        canvas.height = videoElement.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        
        // Flip canvas if we want normal preview mirroring (typically webcam is mirrored)
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(blob => {
            const file = new File([blob], 'snapshot.png', { type: 'image/png' });
            handleImageUpload(file);
            stopWebcam();
        }, 'image/png');
    }

    // Inspect callback triggered from History Panel
    async function handleHistoryInspect(objectName, confidence) {
        activeTab = '📸 Image Scanner';
        selectedExploreLabel = objectName;
        exploreLoading = true;
        exploreResult = null;
        
        // Reset preview url for static inspect representation
        uploadPreviewUrl = '';
        
        // Setup default mock results for visual state representation
        analysisResult = {
            detections: [{ label: objectName, confidence: confidence, box: [0, 0, 0, 0] }],
            latency_ms: 0.0,
            resolution: 'From History',
            annotated_image: null,
            top_label: objectName
        };

        // Step 1: Detection Complete
        scanStep = 1;
        
        // Reset progress bar to 0
        visibleConfidence = {};
        visibleConfidence[objectName] = 0;
        
        // After 600ms, go to Step 2: Confidence Animates
        setTimeout(() => {
            scanStep = 2;
            visibleConfidence[objectName] = confidence;
            
            // After 1000ms (to let confidence bar fill animation show), go to Step 3: Knowledge Loading
            setTimeout(async () => {
                scanStep = 3; // Knowledge Loading
                
                await loadLabelDetails(objectName);
                
                // Once loaded, go to Step 4: Facts Appear Sequentially
                scanStep = 4;
                
                // After 1500ms (let sequential reveal finish), go to Step 5: Learning Ready
                setTimeout(() => {
                    scanStep = 5;
                }, 1500);
            }, 1000);
        }, 600);
    }

    // Markdown Parser Helper
    function parseMarkdown(md) {
        if (!md) return '';
        try {
            return marked.parse(md);
        } catch (e) {
            console.error('Markdown compilation error:', e);
            return md;
        }
    }

    async function startWorkspaceSession(target, subTab = 'quiz') {
        activeTab = '🎓 Study Workspace';
        learningTarget = target;
        await loadLearningCurriculum();
        if (learningData) {
            learningData._activeSubTab = subTab;
        }
    }

    function startComparisonSession(target) {
        compareA = target;
        activeTab = '⚖️ Specimen Comparator';
        if (compareB) {
            executeComparison();
        }
    }
</script>

<!-- Animated Background -->

<div class="app-layout">
    
    <!-- Sidebar Panel -->
    <aside class="sidebar">
        <div class="sidebar-brand">
            <span class="logo-eye">👁️</span>
            <h2>VisionAI</h2>
        </div>
        <p class="sidebar-tagline">Real-Time Object Learning Suite</p>

        <!-- Navigation Menu -->
        <nav class="sidebar-nav">
            {#each ['📸 Image Scanner', '📹 Real-Time Scan', '🔍 Specimen Explorer', '🎓 Study Workspace', '📖 Document Digest', '⏳ Archive Logs', '⚖️ Specimen Comparator', 'ℹ️ Operator Manual'] as tab}
                <button 
                    class="nav-item" 
                    class:active={activeTab === tab} 
                    onclick={() => {
                        activeTab = tab;
                        if (tab !== '📹 Real-Time Scan') stopWebcam();
                    }}
                >
                    {tab}
                </button>
            {/each}
        </nav>

        <!-- Settings Box -->
        <div class="sidebar-section settings-box">
            <h3>⚙️ Settings</h3>
            
            <div class="setting-row">
                <label for="vision-engine">Vision Engine</label>
                <select id="vision-engine" bind:value={visionEngine}>
                    <option value="classification">Classification (MobileNet)</option>
                    <option value="detection">Detection (YOLOv8)</option>
                </select>
            </div>

            <div class="setting-row">
                <div class="slider-header">
                    <label for="conf-thresh">Confidence Threshold</label>
                    <span class="val">{Math.round(confidenceThreshold * 100)}%</span>
                </div>
                <input 
                    id="conf-thresh" 
                    type="range" 
                    min="0.10" 
                    max="0.90" 
                    step="0.05" 
                    bind:value={confidenceThreshold} 
                />
            </div>

            <div class="setting-row toggle-row">
                <label for="demo-mode">🖥️ Enable Demo Mode</label>
                <input 
                    id="demo-mode" 
                    type="checkbox" 
                    bind:checked={enableDemoMode} 
                />
            </div>
        </div>

        <!-- Connection Indicator -->
        <div class="sidebar-section status-indicator">
            {#if statusChecking}
                <span class="indicator checking">🟡 Checking Connection...</span>
            {:else if systemStatus.ollama_active}
                <span class="indicator active">🟢 Ollama Active ({systemStatus.ollama_model})</span>
            {:else}
                <div class="offline-box">
                    <span class="indicator offline">🔴 Ollama Offline</span>
                    <p class="offline-help">Start Ollama locally and run <code>ollama run llama3.2:3b</code> to unlock interactive facts, quizzes, and OCR guides.</p>
                </div>
            {/if}
        </div>
    </aside>

    <!-- Main Content Canvas -->
    <main class="content-canvas">
        <header class="app-header">
            <div class="header-hud">
                <div class="hud-main">
                    <h1>{activeTab}</h1>
                    <p class="operator-greeting">{operatorGreeting}</p>
                </div>
                <div class="hud-stats">
                    <div class="hud-stat-badge emerald-glow">
                        <span class="lbl">STREAK</span>
                        <span class="val">🔥 {studyStreak} Days</span>
                    </div>
                    <div class="hud-stat-badge cyan-glow">
                        <span class="lbl">ARCHIVE</span>
                        <span class="val">👁️ {totalSpecimensCount} Logged</span>
                    </div>
                </div>
            </div>
            
            <div class="fact-ticker">
                <span class="ticker-lbl">DIAGNOSTIC FACT:</span>
                <span class="ticker-val">{activeFact}</span>
            </div>
        </header>

        <!-- Demo Mode metrics dashboard overlay -->
        {#if enableDemoMode}
            <section class="demo-metrics-panel">
                <div class="metric-card indigo-glow">
                    <span class="lbl">Last Detected Label</span>
                    <span class="num">{selectedExploreLabel || 'None'}</span>
                </div>
                <div class="metric-card cyan-glow">
                    <span class="lbl">Inference Latency</span>
                    <span class="num">{analysisResult ? `${analysisResult.latency_ms.toFixed(1)} ms` : '0.0 ms'}</span>
                </div>
                <div class="metric-card violet-glow">
                    <span class="lbl">Detections Count</span>
                    <span class="num">{analysisResult ? analysisResult.detections.length : 0}</span>
                </div>
                <div class="metric-card yellow-glow">
                    <span class="lbl">Active Vision Engine</span>
                    <span class="num">{visionEngine === 'classification' ? 'MobileNetV2' : 'YOLOv8'}</span>
                </div>
            </section>
        {/if}

        <div class="tab-content-wrapper">
            
            <!-- TAB 1: IMAGE SCANNER -->
            {#if activeTab === '📸 Image Scanner'}
                <div class="panel-layout">
                    <!-- Left Side: Upload & View -->
                    <div class="column-left">
                        <div class="glass-card upload-card">
                            <h3>Specimen Diagnostic Scanner</h3>
                            <div class="file-dropzone" class:has-image={uploadPreviewUrl || (analysisResult && analysisResult.annotated_image)}>
                                {#if isAnalyzing && uploadPreviewUrl}
                                    <div class="scanner-preview-wrapper">
                                        <img src={uploadPreviewUrl} alt="Scanning Feed" class="scan-preview-img" />
                                        <div class="scanner-laser"></div>
                                        <div class="scan-overlay-text">RUNNING DIAGNOSTIC SCAN...</div>
                                    </div>
                                {:else if analysisResult && analysisResult.annotated_image}
                                    <div class="scanner-preview-wrapper scan-success">
                                        <img src={analysisResult.annotated_image} alt="Inference Bounding Boxes" class="annotated-img" />
                                        <div class="scan-success-badge">SCAN COMPLETE</div>
                                    </div>
                                {:else}
                                    <input 
                                        type="file" 
                                        accept="image/*" 
                                        id="file-picker" 
                                        onchange={(e) => {
                                            uploadFile = e.target.files[0];
                                            handleImageUpload(uploadFile);
                                        }} 
                                    />
                                    <label for="file-picker" class="picker-label">
                                        <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                                        <span>Click to insert target specimen image</span>
                                    </label>
                                {/if}
                            </div>

                            {#if analysisError}
                                <div class="error-banner">{analysisError}</div>
                            {/if}

                            {#if analysisResult}
                                <div class="inference-stats">
                                    <h4>Inference Diagnostic Telemetry</h4>
                                    <div class="stats-grid">
                                        <div class="stat-item"><span class="lbl">Latency</span><span class="val">{analysisResult.latency_ms.toFixed(1)} ms</span></div>
                                        <div class="stat-item"><span class="lbl">Frame Matrix</span><span class="val">{analysisResult.resolution}</span></div>
                                        <div class="stat-item"><span class="lbl">Targets</span><span class="val">{analysisResult.detections.length}</span></div>
                                    </div>
                                </div>

                                <div class="detections-list">
                                    <h4>Identified Specimens</h4>
                                    {#each analysisResult.detections as det}
                                        <div class="det-list-item">
                                            <div class="det-meta">
                                                <span class="det-label">{det.label}</span>
                                                <span class="det-pct">{Math.round((visibleConfidence[det.label] || 0) * 100)}% Match</span>
                                            </div>
                                            <div class="progress-bar-track">
                                                <div class="progress-bar-fill" style="width: {(visibleConfidence[det.label] || 0) * 100}%"></div>
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    </div>

                    <!-- Right Side: LLM Knowledge Profile -->
                    <div class="column-right">
                        <div class="glass-card facts-card">
                            {#if selectedExploreLabel}
                                <div class="facts-header">
                                    <h3>🎓 Knowledge Engine: {selectedExploreLabel}</h3>
                                    {#if scanStep === 1}
                                        <span class="status-pill status-success">✓ DETECTION COMPLETE</span>
                                    {:else if scanStep === 2}
                                        <span class="status-pill status-info">⚡ ANALYZING CONFIDENCE...</span>
                                    {:else if scanStep === 3}
                                        <span class="status-pill status-loading">🧠 AI SYNTHESIS LOADING...</span>
                                    {:else if scanStep === 4}
                                        <span class="status-pill status-compiling">📚 RENDERING CURRICULUM...</span>
                                    {:else if scanStep === 5}
                                        <span class="status-pill status-ready">🟢 LEARNING READY</span>
                                    {/if}
                                </div>

                                {#if scanStep === 1 || scanStep === 2}
                                    <div class="discovery-step-view">
                                        <div class="discovery-pulse-container">
                                            <div class="pulse-icon">🔍</div>
                                            <div class="pulse-waves"></div>
                                        </div>
                                        <p class="discovery-text">Specimen matched successfully. Syncing confidence scores...</p>
                                    </div>
                                {:else if scanStep === 3}
                                    <div class="discovery-step-view">
                                        <div class="discovery-loading-spinner">
                                            <div class="spinner-core"></div>
                                        </div>
                                        <p class="discovery-text">AI Agent is compiling educational overview, taxonomy details, key characteristics, and learning notes...</p>
                                    </div>
                                {:else if scanStep >= 4}
                                    {#if exploreResult}
                                        <div class="facts-viewport">
                                            <ReadingHighlighter text={exploreResult} />
                                        </div>
                                    {:else}
                                        <p class="fallback-note">Ollama is offline. Start the service to compile facts.</p>
                                    {/if}
                                    
                                    {#if scanStep === 5}
                                        <!-- Interactive Study Integration -->
                                        <div class="hud-study-actions slide-up-reveal">
                                            <h4>⚡ Specimen Action Suite</h4>
                                            <div class="study-actions-grid">
                                                <button class="action-btn study-btn active-pulse" onclick={() => startWorkspaceSession(selectedExploreLabel, 'quiz')}>
                                                    🎓 Run MCQ Quiz
                                                </button>
                                                <button class="action-btn study-btn" onclick={() => startWorkspaceSession(selectedExploreLabel, 'flash')}>
                                                    🎴 Study Flashcards
                                                </button>
                                                <button class="action-btn study-btn" onclick={() => startWorkspaceSession(selectedExploreLabel, 'explain')}>
                                                    📖 Full Details
                                                </button>
                                                <button class="action-btn compare-btn" onclick={() => startComparisonSession(selectedExploreLabel)}>
                                                    ⚖️ Compare Target
                                                </button>
                                            </div>
                                        </div>
                                        
                                        <!-- Chat Widget -->
                                        <div class="chat-widget slide-up-reveal" style="animation-delay: 200ms;">
                                            <h4>💬 Ask About This Object</h4>
                                            <div class="chat-viewport">
                                                {#each chatHistory as msg}
                                                    <div class="chat-bubble {msg.role}">
                                                        <span class="sender-tag">{msg.role === 'user' ? 'You' : 'Assistant'}</span>
                                                        <p>{msg.content}</p>
                                                    </div>
                                                {/each}
                                                {#if chatLoading}
                                                    <div class="chat-bubble assistant loading">
                                                        <div class="typing-indicator"><span></span><span></span><span></span></div>
                                                    </div>
                                                {/if}
                                            </div>
                                            <form class="chat-form" onsubmit={(e) => { e.preventDefault(); sendChatMessage(); }}>
                                                <input 
                                                    type="text" 
                                                    placeholder="Ask a question about this object..." 
                                                    bind:value={chatMessageInput} 
                                                />
                                                <button type="submit" disabled={chatLoading || !chatMessageInput.trim()}>
                                                    Send
                                                </button>
                                            </form>
                                        </div>
                                    {/if}
                                {/if}
                            {:else}
                                <div class="empty-facts-state">
                                    <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                                    <p>Select or upload an image to identify objects and load details.</p>
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>
            {/if}

            <!-- TAB 2: REAL-TIME SCAN -->
            {#if activeTab === '📹 Real-Time Scan'}
                <div class="glass-card live-capture-card">
                    <div class="video-preview-wrapper">
                        {#if !isWebcamActive}
                            <div class="camera-placeholder">
                                <svg viewBox="0 0 24 24" width="60" height="60" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                                <button class="start-camera-btn" onclick={startWebcam}>Enable Scanner Camera</button>
                            </div>
                        {/if}
                        <video bind:this={videoElement} class:active={isWebcamActive} autoplay playsinline><track kind="captions" /></video>
                    </div>

                    {#if isWebcamActive}
                        <div class="camera-actions">
                            <button class="snap-btn" onclick={captureSnapshot}>📸 Scan Frame</button>
                            <button class="stop-camera-btn" onclick={stopWebcam}>Stop Scan</button>
                        </div>
                    {/if}
                </div>
            {/if}

            <!-- TAB 3: SPECIMEN EXPLORER -->
            {#if activeTab === '🔍 Specimen Explorer'}
                <div class="glass-card search-card">
                    <div class="search-input-row">
                        <input 
                            type="text" 
                            placeholder="Query cataloged specimen, e.g. Tiger, Elephant, Laptop..." 
                            bind:value={searchQuery}
                            onkeydown={(e) => e.key === 'Enter' && executeSearch()}
                        />
                        <button onclick={executeSearch} disabled={searchLoading}>
                            {searchLoading ? 'Searching...' : 'Explore Knowledge'}
                        </button>
                    </div>

                    {#if searchError}
                        <div class="error-banner">{searchError}</div>
                    {/if}

                    {#if searchResult}
                        <div class="search-results-panel">
                            <div class="results-columns">
                                
                                <!-- Wiki side -->
                                <div class="col-wiki">
                                    <h4>Wikipedia Profile</h4>
                                    {#if searchResult.image_url}
                                        <img src={searchResult.image_url} alt={searchResult.query} class="search-wiki-img" />
                                    {/if}
                                    {#if searchResult.wikipedia_summary}
                                        <div class="wiki-text-box">{searchResult.wikipedia_summary}</div>
                                    {:else}
                                        <p class="no-wiki-text">No summary page found on Wikipedia.</p>
                                    {/if}
                                </div>

                                <!-- LLM side -->
                                <div class="col-llm">
                                    <div class="facts-header">
                                        <h4>Ollama AI Fact Sheet</h4>
                                    </div>
                                    {#if searchResult.llm_info}
                                        <ReadingHighlighter text={searchResult.llm_info} />
                                        
                                        <!-- Interactive Study Integration -->
                                        <div class="hud-study-actions border-top">
                                            <h4>⚡ Specimen Action Suite</h4>
                                            <div class="study-actions-grid">
                                                <button class="action-btn study-btn" onclick={() => startWorkspaceSession(searchQuery, 'quiz')}>
                                                    🎓 Run MCQ Quiz
                                                </button>
                                                <button class="action-btn study-btn" onclick={() => startWorkspaceSession(searchQuery, 'flash')}>
                                                    🎴 Study Flashcards
                                                </button>
                                                <button class="action-btn study-btn" onclick={() => startWorkspaceSession(searchQuery, 'explain')}>
                                                    📖 Full Details
                                                </button>
                                                <button class="action-btn compare-btn" onclick={() => startComparisonSession(searchQuery)}>
                                                    ⚖️ Compare Target
                                                </button>
                                            </div>
                                        </div>
                                    {:else}
                                        <p class="offline-note">Ollama connection is offline. Launch local LLM to generate educational guides.</p>
                                    {/if}
                                </div>

                            </div>
                        </div>
                    {/if}
                </div>
            {/if}

            <!-- TAB 4: STUDY WORKSPACE -->
            {#if activeTab === '🎓 Study Workspace'}
                <div class="glass-card learning-card">
                    <div class="learning-header-input">
                        <div class="input-col">
                            <label for="learn-target">Concept / Object</label>
                            <input 
                                id="learn-target"
                                type="text" 
                                placeholder="Concept to study, e.g. Tiger, Quantum, Laptop..." 
                                bind:value={learningTarget}
                            />
                        </div>
                        <button class="generate-learn-btn" onclick={loadLearningCurriculum} disabled={learningLoading}>
                            {learningLoading ? 'Compiling Workspace...' : '💡 Explore Knowledge'}
                        </button>
                    </div>

                    {#if learningError}
                        <div class="error-banner">{learningError}</div>
                    {/if}

                    {#if learningLoading}
                        <div class="learning-loading">
                            <div class="spinner"></div>
                            <p>Ollama model is compiling flashcards, MCQs, and viva voce revision lists. This might take 10-15 seconds...</p>
                        </div>
                    {/if}

                    {#if learningData}
                        <div class="learning-tabs-panel">
                            <!-- Custom Tab Selectors -->
                            <div class="tabs-subnav">
                                {#each ['Full Explanation', 'Interactive Quiz', 'Digital Flashcards', 'Revision Notes', 'Viva Preparation'] as subTab}
                                    <button 
                                        class="subnav-item" 
                                        class:active={subTab === 'Full Explanation' ? !learningData._activeSubTab || learningData._activeSubTab === 'explain' : 
                                                      subTab === 'Interactive Quiz' ? learningData._activeSubTab === 'quiz' : 
                                                      subTab === 'Digital Flashcards' ? learningData._activeSubTab === 'flash' :
                                                      subTab === 'Revision Notes' ? learningData._activeSubTab === 'notes' : 
                                                      learningData._activeSubTab === 'viva'}
                                        onclick={() => {
                                            learningData._activeSubTab = 
                                                subTab === 'Full Explanation' ? 'explain' :
                                                subTab === 'Interactive Quiz' ? 'quiz' :
                                                subTab === 'Digital Flashcards' ? 'flash' :
                                                subTab === 'Revision Notes' ? 'notes' : 'viva';
                                        }}
                                    >
                                        {subTab}
                                    </button>
                                {/each}
                            </div>

                            <div class="sub-tab-content">
                                {#if !learningData._activeSubTab || learningData._activeSubTab === 'explain'}
                                    <div class="explanation-box">
                                        <ReadingHighlighter text={learningData.full_explanation} />
                                    </div>
                                {:else if learningData._activeSubTab === 'quiz'}
                                    <QuizComponent mcqs={learningData.mcqs} targetObject={learningTarget} />
                                {:else if learningData._activeSubTab === 'flash'}
                                    <FlashcardDeck flashcards={learningData.flashcards} />
                                {:else if learningData._activeSubTab === 'notes'}
                                    <div class="revision-notes-box">
                                        <ReadingHighlighter text={learningData.revision_notes} />
                                    </div>
                                {:else if learningData._activeSubTab === 'viva'}
                                    <div class="viva-deck">
                                        {#each learningData.viva as item, i}
                                            <details class="viva-expander">
                                                <summary>Question {i+1}: {item.question}</summary>
                                                <div class="viva-answer">{item.answer}</div>
                                            </details>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}

            <!-- TAB 5: DOCUMENT DIGEST -->
            {#if activeTab === '📖 Document Digest'}
                <div class="glass-card ocr-card">
                    <div class="ocr-inputs">
                        <label for="ocr-picker" class="ocr-upload-lbl">
                            <input 
                                type="file" 
                                accept="image/*" 
                                id="ocr-picker" 
                                onchange={(e) => {
                                    ocrFile = e.target.files[0];
                                    executeOCR();
                                }} 
                            />
                            <span>Upload Page / Document Image</span>
                        </label>
                    </div>

                    {#if ocrLoading}
                        <div class="loading-state">
                            <div class="spinner"></div>
                            <p>Running OCR engines and generating AI summaries...</p>
                        </div>
                    {/if}

                    {#if ocrError}
                        <div class="error-banner">{ocrError}</div>
                    {/if}

                    {#if ocrResult}
                        <div class="ocr-results-layout">
                            <div class="extracted-text-section">
                                <div class="sec-header">
                                    <h4>Raw Extracted Text</h4>
                                    <span class="ocr-badge">{ocrResult.method}</span>
                                </div>
                                <textarea readonly class="text-area-raw">{ocrResult.text}</textarea>
                            </div>

                            <div class="ocr-analysis-section">
                                <div class="sec-header">
                                    <h4>AI Analysis & Study Guide</h4>
                                </div>

                                {#if ocrResult.analysis}
                                    <ReadingHighlighter text={ocrResult.analysis} />
                                    <a 
                                        href="data:text/plain;charset=utf-8,{encodeURIComponent('Raw OCR Text:\n' + ocrResult.text + '\n\nAI Summary:\n' + ocrResult.analysis)}" 
                                        download="study_guide.txt"
                                        class="download-btn"
                                        style="margin-top: 1rem;"
                                    >
                                        📥 Download Study Guide as TXT
                                    </a>
                                {:else}
                                    <p class="offline-note">Ollama is offline. Start local LLM to automatically generate summaries and exam questions.</p>
                                	{/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}

            <!-- TAB 6: ARCHIVE LOGS -->
            {#if activeTab === '⏳ Archive Logs'}
                <div class="glass-card history-panel-card">
                    <HistoryPanel onInspect={handleHistoryInspect} onUpdateCount={(count) => { totalSpecimensCount = count; }} />
                </div>
            {/if}

            <!-- TAB 7: SPECIMEN COMPARATOR -->
            {#if activeTab === '⚖️ Specimen Comparator'}
                <div class="glass-card compare-card">
                    <div class="compare-inputs-row">
                        <div class="comp-col">
                            <label for="comp-a">Object A</label>
                            <input id="comp-a" type="text" bind:value={compareA} />
                        </div>
                        <span class="vs">VS</span>
                        <div class="comp-col">
                            <label for="comp-b">Object B</label>
                            <input id="comp-b" type="text" bind:value={compareB} />
                        </div>
                        <button onclick={executeComparison} disabled={compareLoading}>
                            {compareLoading ? 'Analyzing...' : '⚖️ Compare Specimens'}
                        </button>
                    </div>

                    {#if compareError}
                        <div class="error-banner">{compareError}</div>
                    {/if}

                    {#if compareLoading}
                        <div class="loading-state">
                            <div class="spinner"></div>
                            <p>Ollama model is conducting concept comparative studies...</p>
                        </div>
                    {/if}

                    {#if compareResult}
                        <div class="compare-results">
                            <ReadingHighlighter text={compareResult} />
                        </div>
                    {/if}
                </div>
            {/if}

            <!-- TAB 8: OPERATOR MANUAL -->
            {#if activeTab === 'ℹ️ Operator Manual'}
                <div class="manual-layout">
                    <!-- Workflow Pipeline Diagram -->
                    <div class="manual-section pipeline-section">
                        <h3>Diagnostic Discovery Pipeline</h3>
                        <p class="section-subtitle">Tactical flow mapping specimen capture to local generative synthesis</p>
                        
                        <div class="manual-pipeline">
                            <div class="pipeline-node indigo-glow">
                                <span class="icon">📸</span>
                                <span class="lbl">Capture Feed</span>
                                <span class="desc">Snapshot snap / file upload</span>
                            </div>
                            <div class="pipeline-arrow">➔</div>
                            <div class="pipeline-node cyan-glow">
                                <span class="icon">🧠</span>
                                <span class="lbl">Vision Inference</span>
                                <span class="desc">YOLOv8 / MobileNet engine</span>
                            </div>
                            <div class="pipeline-arrow">➔</div>
                            <div class="pipeline-node emerald-glow">
                                <span class="icon">📚</span>
                                <span class="lbl">LLM Synthesis</span>
                                <span class="desc">Ollama curriculum generator</span>
                            </div>
                            <div class="pipeline-arrow">➔</div>
                            <div class="pipeline-node yellow-glow">
                                <span class="icon">💾</span>
                                <span class="lbl">Local Archive</span>
                                <span class="desc">SQLite database logging</span>
                            </div>
                        </div>
                    </div>

                    <div class="panel-layout double-col">
                        <!-- Left Side: System Architecture -->
                        <div class="column-left flex-col gap-md">
                            <div class="glass-card compact">
                                <h3>Vision Engine Architecture</h3>
                                <p class="desc-text">VisionAI operates through a decoupled dual-engine offline computer vision pipeline:</p>
                                <div class="tech-grid">
                                    <div class="tech-card">
                                        <span class="tech-title">MobileNetV2 (Classification)</span>
                                        <p>Executes custom contour-detection crops on regions of interest, resizes targets to 224x224, and feeds matrices natively into ONNX weights.</p>
                                    </div>
                                    <div class="tech-card">
                                        <span class="tech-title">YOLOv8 Nano (Detection)</span>
                                        <p>Evaluates full-frame imagery directly at 640x640 resolutions, outputs label coordinates, and applies Non-Maximum Suppression (NMS) to eliminate overlapping bounding boxes.</p>
                                    </div>
                                </div>
                            </div>

                            <div class="glass-card compact">
                                <h3>Offline Local Generative AI</h3>
                                <p class="desc-text">Ollama services read local configurations, pulling <code>llama3.2:3b</code> models on host machines, ensuring complete network privacy and low latency caching locally in <code>llm_cache.json</code>.</p>
                            </div>
                        </div>

                        <!-- Right Side: Operator Instructions -->
                        <div class="column-right">
                            <div class="glass-card operator-instructions-card">
                                <h3>Tactical Operations Catalog</h3>
                                <div class="instructions-list">
                                    <div class="instruction-item">
                                        <span class="item-head">📸 Image Scanner & Chat</span>
                                        <p>Feed a static image file or snaps to identify labels. Ask the interactive chat widget contextual queries to explore specific structural properties.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">📹 Real-Time Scan</span>
                                        <p>Toggle your webcam to dynamically capture diagnostic frames and inspect physical objects in real-time.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">🔍 Specimen Explorer</span>
                                        <p>Query Wikipedia databases for encyclopedia entries, download reference illustrations, and pull structured Ollama fact sheets offline.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">🎓 Study Workspace</span>
                                        <p>Compile a custom learning curriculum containing detailed summaries, 3D flashcard decks, interactive quizzes, and oral revision items.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">📖 Document Digest</span>
                                        <p>Upload worksheets or documents to extract printable text using OCR and parse summary notes. Listen to summaries read aloud via speech synthesis.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">⏳ Archive Logs</span>
                                        <p>Inspect previous diagnostic reports, reload historical specimens to run study workflows, or clear log tables.</p>
                                    </div>
                                    <div class="instruction-item">
                                        <span class="item-head">⚖️ Specimen Comparator</span>
                                        <p>Select two arbitrary concepts to output side-by-side matrices contrasting their size, habitats, composition, functions, and key insights.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}

        </div>
    </main>

</div>

<style>
    /* Global Layout styling */
    .app-layout {
        display: flex;
        min-height: 100vh;
        width: 100vw;
        overflow-x: hidden;
        position: relative;
        z-index: 1;
    }

    /* Sidebar Panels */
    .sidebar {
        width: 280px;
        background: rgba(11, 15, 27, 0.7);
        backdrop-filter: blur(25px);
        border-right: 1px solid var(--border);
        padding: 2rem 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        flex-shrink: 0;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .logo-eye {
        font-size: 2rem;
        animation: float-eye 4s ease-in-out infinite;
    }

    @keyframes float-eye {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }

    .sidebar-brand h2 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .sidebar-tagline {
        margin: -1rem 0 0 0;
        font-size: 0.85rem;
        color: var(--text-muted);
        letter-spacing: 0.05em;
    }

    .sidebar-nav {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .nav-item {
        background: transparent;
        border: none;
        color: var(--text-secondary);
        padding: 12px 16px;
        text-align: left;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 500;
        font-size: 0.95rem;
        transition: all 0.3s ease;
    }

    .nav-item:hover {
        background: rgba(255, 255, 255, 0.04);
        color: var(--text-primary);
        transform: translateX(4px);
    }

    .nav-item.active {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(6, 182, 212, 0.12));
        border: 1px solid rgba(99, 102, 241, 0.25);
        color: var(--primary);
        font-weight: 600;
        box-shadow: var(--glow-indigo);
    }

    /* Sidebar settings */
    .sidebar-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 16px;
        padding: 1.2rem;
    }

    .sidebar-section h3 {
        margin: 0 0 1rem 0;
        font-size: 0.95rem;
        color: var(--text-primary);
    }

    .setting-row {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 1rem;
    }

    .setting-row:last-child {
        margin-bottom: 0;
    }

    .setting-row label {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .setting-row select {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid var(--border);
        color: var(--text-primary);
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        outline: none;
    }

    .slider-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .slider-header .val {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--accent);
    }

    .setting-row input[type="range"] {
        accent-color: var(--accent);
        background: rgba(255, 255, 255, 0.1);
        height: 6px;
        border-radius: 6px;
        outline: none;
    }

    .toggle-row {
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
    }

    .toggle-row label {
        margin: 0;
        cursor: pointer;
    }

    .toggle-row input {
        cursor: pointer;
        width: 16px;
        height: 16px;
    }

    .indicator {
        font-size: 0.85rem;
        font-weight: 600;
    }

    .offline-box {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .offline-help {
        margin: 0;
        font-size: 0.72rem;
        line-height: 1.35;
        color: var(--text-muted);
    }

    .offline-help code {
        background: rgba(239, 68, 68, 0.08);
        color: #ef4444;
        padding: 2px 4px;
        border-radius: 4px;
    }

    /* Main Content Canvas */
    .content-canvas {
        flex-grow: 1;
        min-width: 0;
        padding: 2rem 2.5rem;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        overflow-y: auto;
        max-height: 100vh;
        box-sizing: border-box;
    }

    .tab-content-wrapper {
        width: 100%;
        flex-grow: 1;
        box-sizing: border-box;
    }

    .app-header h1 {
        margin: 0 0 0.25rem 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .header-desc {
        margin: 0;
        font-size: 1.05rem;
        color: var(--text-secondary);
    }

    /* Demo dashboard overlay */
    .demo-metrics-panel {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 0.5rem;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 4px;
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-4px);
    }

    .indigo-glow:hover { box-shadow: var(--glow-indigo); border-color: rgba(99, 102, 241, 0.3); }
    .cyan-glow:hover { box-shadow: var(--glow-cyan); border-color: rgba(6, 182, 212, 0.3); }
    .violet-glow:hover { box-shadow: 0 0 25px rgba(168, 85, 247, 0.15); border-color: rgba(168, 85, 247, 0.3); }
    .yellow-glow:hover { box-shadow: 0 0 25px rgba(234, 179, 8, 0.15); border-color: rgba(234, 179, 8, 0.3); }

    .metric-card .lbl {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
    }

    .metric-card .num {
        font-size: 1.45rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: var(--bg-card);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
        box-sizing: border-box;
    }

    /* Column Panels */
    .panel-layout {
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 1.5rem;
        align-items: start;
        max-width: 1200px;
        width: 100%;
        margin: 0 auto;
        box-sizing: border-box;
    }

    @media (max-width: 1000px) {
        .panel-layout {
            grid-template-columns: 1fr;
        }
    }

    /* Analyze image styles */
    .file-dropzone {
        border: 2px dashed var(--border);
        border-radius: 16px;
        padding: 2.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        background: rgba(255, 255, 255, 0.01);
    }

    .file-dropzone input {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0;
        cursor: pointer;
    }

    .file-dropzone:hover {
        border-color: var(--primary);
        background: rgba(99, 102, 241, 0.02);
    }

    .picker-label {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        color: var(--text-secondary);
    }

    .picker-label span {
        font-weight: 500;
        font-size: 0.95rem;
    }

    .analyzer-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-top: 1.5rem;
        gap: 10px;
    }

    .analyzer-loading p {
        color: var(--text-secondary);
        font-size: 0.9rem;
    }

    .spinner {
        width: 24px;
        height: 24px;
        border: 2px solid rgba(255, 255, 255, 0.1);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .error-banner {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #f87171;
        padding: 12px;
        border-radius: 12px;
        font-size: 0.9rem;
        margin-top: 1rem;
    }

    .inference-stats {
        margin-top: 1.5rem;
    }

    .inference-stats h4 {
        margin: 0 0 10px 0;
        font-size: 0.95rem;
        color: var(--text-secondary);
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }

    .stat-item {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .stat-item .lbl {
        font-size: 0.72rem;
        color: var(--text-muted);
        font-weight: 700;
        text-transform: uppercase;
    }

    .stat-item .val {
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .image-output {
        margin-top: 1.5rem;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    .annotated-img {
        width: 100%;
        height: auto;
        display: block;
    }

    .detections-list {
        margin-top: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .detections-list h4 {
        margin: 0;
        font-size: 0.95rem;
        color: var(--text-secondary);
    }

    .det-list-item {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 14px;
    }

    .det-meta {
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
    }

    .det-label {
        font-weight: 600;
        color: var(--text-primary);
    }

    .det-pct {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--primary);
    }

    .progress-bar-track {
        height: 6px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        overflow: hidden;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        border-radius: 4px;
    }

    /* Facts side panel styles */
    .facts-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border);
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }

    .facts-header h3, .facts-header h4 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 700;
    }

    .tts-btn {
        border: none;
        padding: 8px 16px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.25s ease;
    }

    .tts-btn.play {
        background: rgba(6, 182, 212, 0.08);
        border: 1px solid rgba(6, 182, 212, 0.2);
        color: #06b6d4;
    }

    .tts-btn.play:hover {
        background: rgba(6, 182, 212, 0.16);
        transform: translateY(-1px);
    }

    .tts-btn.stop {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        color: #f87171;
    }

    .tts-btn.stop:hover {
        background: rgba(239, 68, 68, 0.18);
        transform: translateY(-1px);
    }

    /* Markdown styling */
    .markdown-content :global(h3) {
        font-size: 1.2rem;
        color: var(--primary);
        margin: 1.5rem 0 0.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 4px;
    }

    .markdown-content :global(h3:first-of-type) {
        margin-top: 0;
    }

    .markdown-content :global(p) {
        font-size: 0.95rem;
        line-height: 1.6;
        color: var(--text-secondary);
        margin: 0 0 1rem 0;
    }

    .markdown-content :global(ul) {
        margin: 0 0 1rem 0;
        padding-left: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .markdown-content :global(li) {
        font-size: 0.95rem;
        line-height: 1.5;
        color: var(--text-secondary);
    }

    .markdown-content :global(strong) {
        color: var(--text-primary);
    }

    .markdown-content :global(table) {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    .markdown-content :global(th) {
        background: rgba(255, 255, 255, 0.03);
        padding: 10px 14px;
        text-align: left;
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--accent);
        border-bottom: 1px solid var(--border);
    }

    .markdown-content :global(td) {
        padding: 10px 14px;
        font-size: 0.88rem;
        color: var(--text-secondary);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }

    .markdown-content :global(tr:last-child td) {
        border-bottom: none;
    }

    .empty-facts-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 5rem 2rem;
        text-align: center;
        color: var(--text-muted);
        gap: 12px;
    }

    .empty-facts-state p {
        font-size: 0.95rem;
        max-width: 250px;
        margin: 0;
        line-height: 1.4;
    }

    /* Chat styling */
    .chat-widget {
        margin-top: 2rem;
        border-top: 1px solid var(--border);
        padding-top: 1.5rem;
    }

    .chat-widget h4 {
        margin: 0 0 12px 0;
        font-size: 0.95rem;
        color: var(--text-secondary);
    }

    .chat-viewport {
        max-height: 280px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 14px;
        padding: 1rem;
        border: 1px solid var(--border);
        margin-bottom: 12px;
    }

    .chat-bubble {
        display: flex;
        flex-direction: column;
        max-width: 80%;
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 0.92rem;
        line-height: 1.4;
    }

    .chat-bubble.assistant {
        align-self: flex-start;
        background: rgba(255, 255, 255, 0.04);
        color: var(--text-primary);
        border: 1px solid var(--border);
    }

    .chat-bubble.user {
        align-self: flex-end;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(6, 182, 212, 0.15));
        color: var(--text-primary);
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

    .sender-tag {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }

    .chat-bubble.assistant .sender-tag { color: var(--accent); }
    .chat-bubble.user .sender-tag { color: var(--primary); }

    .chat-bubble p {
        margin: 0;
    }

    .chat-bubble.loading {
        padding: 12px 18px;
    }

    .typing-indicator {
        display: flex;
        gap: 4px;
        align-items: center;
        height: 14px;
    }

    .typing-indicator span {
        width: 6px;
        height: 6px;
        background: var(--text-muted);
        border-radius: 50%;
        animation: typing 1s infinite ease-in-out;
    }

    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes typing {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }

    .chat-form {
        display: flex;
        gap: 10px;
    }

    .chat-form input {
        flex-grow: 1;
        background: rgba(0, 0, 0, 0.35);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 16px;
        color: var(--text-primary);
        outline: none;
        font-size: 0.92rem;
        transition: all 0.3s ease;
    }

    .chat-form input:focus {
        border-color: var(--accent);
        box-shadow: 0 0 10px rgba(6, 182, 212, 0.1);
    }

    .chat-form button {
        background: var(--accent);
        border: none;
        color: var(--bg-dark);
        padding: 0 20px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease;
    }

    .chat-form button:hover:not(:disabled) {
        opacity: 0.9;
        transform: translateY(-1px);
    }

    .chat-form button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    /* Live capture tab */
    .live-capture-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5rem;
        max-width: 1200px;
        width: 100%;
        margin: 0 auto;
        box-sizing: border-box;
    }

    .video-preview-wrapper {
        width: 100%;
        aspect-ratio: 16/9;
        border-radius: 16px;
        overflow: hidden;
        background: #090d16;
        border: 1px solid var(--border);
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: none;
    }

    video.active {
        display: block;
    }

    .camera-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5rem;
        color: var(--text-muted);
    }

    .start-camera-btn, .snap-btn {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        border: none;
        color: white;
        padding: 12px 30px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: var(--glow-indigo);
        transition: all 0.3s ease;
    }

    .start-camera-btn:hover, .snap-btn:hover {
        transform: translateY(-2px);
        opacity: 0.95;
    }

    .camera-actions {
        display: flex;
        gap: 1rem;
    }

    .stop-camera-btn {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border);
        color: var(--text-secondary);
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease;
    }

    .stop-camera-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: var(--text-primary);
    }

    /* Search Object styles */
    .search-card, .learning-card, .ocr-card, .compare-card, .history-panel-card {
        max-width: 1200px;
        width: 100%;
        margin: 0 auto;
        box-sizing: border-box;
    }

    .search-input-row, .learning-header-input, .compare-inputs-row {
        display: flex;
        gap: 12px;
        align-items: flex-end;
    }

    .search-input-row input, .input-col input, .comp-col input {
        flex-grow: 1;
        background: rgba(0, 0, 0, 0.25);
        border: 1px solid var(--border);
        color: var(--text-primary);
        padding: 14px 18px;
        border-radius: 12px;
        outline: none;
        font-size: 0.95rem;
        transition: all 0.3s ease;
    }

    .search-input-row input:focus, .input-col input:focus, .comp-col input:focus {
        border-color: var(--primary);
    }

    .search-input-row button, .generate-learn-btn, .compare-inputs-row button {
        background: var(--primary);
        border: none;
        color: white;
        padding: 14px 28px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease;
        height: 50px;
        flex-shrink: 0;
    }

    .search-input-row button:hover, .generate-learn-btn:hover, .compare-inputs-row button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }

    .search-results-panel {
        margin-top: 2rem;
    }

    .results-columns {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
    }

    @media (max-width: 800px) {
        .results-columns {
            grid-template-columns: 1fr;
        }
    }

    .col-wiki, .col-llm {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .col-wiki h4, .col-llm h4 {
        margin: 0;
        font-size: 1.15rem;
        font-weight: 700;
        border-bottom: 1px solid var(--border);
        padding-bottom: 8px;
    }

    .search-wiki-img {
        width: 100%;
        height: 220px;
        object-fit: cover;
        border-radius: 14px;
        border: 1px solid var(--border);
    }

    .wiki-text-box {
        background: rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        font-size: 0.92rem;
        line-height: 1.5;
        color: var(--text-secondary);
    }

    /* Learning Mode styles */
    .learning-header-input {
        margin-bottom: 2rem;
    }

    .input-col {
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex-grow: 1;
    }

    .input-col label, .comp-col label {
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .learning-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        text-align: center;
        gap: 1rem;
    }

    .learning-loading p {
        color: var(--text-secondary);
        font-size: 0.95rem;
        max-width: 400px;
        line-height: 1.5;
    }

    .tabs-subnav {
        display: flex;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
        gap: 1rem;
    }

    .subnav-item {
        background: transparent;
        border: none;
        color: var(--text-secondary);
        padding: 10px 14px;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.92rem;
        border-bottom: 2px solid transparent;
        transition: all 0.25s ease;
    }

    .subnav-item:hover {
        color: var(--text-primary);
    }

    .subnav-item.active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .explanation-box, .revision-notes-box {
        background: rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.8rem;
    }

    .viva-deck {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .viva-expander {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    .viva-expander[open] {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(6, 182, 212, 0.2);
    }

    .viva-expander summary {
        padding: 14px 18px;
        font-weight: 600;
        color: var(--text-primary);
        cursor: pointer;
        outline: none;
        list-style: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .viva-expander summary::after {
        content: '▼';
        font-size: 0.75rem;
        color: var(--text-muted);
        transition: transform 0.25s ease;
    }

    .viva-expander[open] summary::after {
        transform: rotate(180deg);
        color: var(--accent);
    }

    .viva-answer {
        padding: 0 18px 18px 18px;
        font-size: 0.95rem;
        line-height: 1.5;
        color: var(--text-secondary);
        border-top: 1px solid rgba(255, 255, 255, 0.03);
        padding-top: 12px;
    }

    /* OCR reader styles */
    .ocr-inputs {
        margin-bottom: 1.5rem;
    }

    .ocr-upload-lbl {
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px dashed var(--border);
        border-radius: 14px;
        padding: 2rem;
        cursor: pointer;
        background: rgba(255, 255, 255, 0.01);
        transition: all 0.25s ease;
    }

    .ocr-upload-lbl:hover {
        border-color: var(--accent);
        background: rgba(6, 182, 212, 0.02);
    }

    .ocr-upload-lbl input {
        display: none;
    }

    .ocr-upload-lbl span {
        color: var(--text-secondary);
        font-weight: 600;
    }

    .ocr-results-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin-top: 1.5rem;
    }

    @media (max-width: 800px) {
        .ocr-results-layout {
            grid-template-columns: 1fr;
        }
    }

    .sec-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border);
        padding-bottom: 8px;
        margin-bottom: 12px;
    }

    .sec-header h4 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 700;
    }

    .ocr-badge {
        font-size: 0.72rem;
        font-weight: 700;
        background: rgba(6, 182, 212, 0.1);
        color: var(--accent);
        border: 1px solid rgba(6, 182, 212, 0.2);
        padding: 2px 8px;
        border-radius: 4px;
    }

    .text-area-raw {
        width: 100%;
        height: 350px;
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem;
        box-sizing: border-box;
        color: var(--text-secondary);
        font-family: monospace;
        font-size: 0.88rem;
        line-height: 1.4;
        resize: none;
        outline: none;
    }

    .scroll-box {
        height: 350px;
        overflow-y: auto;
        background: rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.2rem;
        box-sizing: border-box;
        margin-bottom: 1rem;
    }

    .download-btn {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border);
        color: var(--text-primary);
        padding: 10px 20px;
        border-radius: 10px;
        font-size: 0.88rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.25s ease;
    }

    .download-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-1px);
    }

    /* Comparison styles */
    .compare-inputs-row {
        margin-bottom: 2rem;
    }

    .comp-col {
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex-grow: 1;
    }

    .compare-inputs-row .vs {
        font-size: 1.15rem;
        font-weight: 800;
        color: var(--text-muted);
        align-self: center;
        padding: 0 0.5rem 10px 0.5rem;
    }

    .compare-results {
        background: rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 2rem;
    }

    /* Fallback notes */
    .offline-note {
        margin: 0;
        font-size: 0.9rem;
        color: #f87171;
        background: rgba(239, 68, 68, 0.06);
        border: 1px dashed rgba(239, 68, 68, 0.15);
        padding: 1rem;
        border-radius: 12px;
        line-height: 1.4;
    }

    .fallback-note {
        margin: 0;
        font-size: 0.9rem;
        color: var(--text-muted);
        text-align: center;
        padding: 2rem 0;
    }

    /* Header HUD */
    .header-hud {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1.5rem;
        border-bottom: 1px solid var(--border);
        padding-bottom: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .hud-main {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    
    .operator-greeting {
        margin: 0;
        font-size: 0.95rem;
        color: var(--text-secondary);
        font-weight: 500;
    }

    .hud-stats {
        display: flex;
        gap: 1rem;
    }

    .hud-stat-badge {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border);
        padding: 8px 16px;
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 2px;
        min-width: 120px;
        transition: all 0.3s ease;
    }
    
    .hud-stat-badge .lbl {
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .hud-stat-badge .val {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .emerald-glow:hover {
        box-shadow: var(--glow-emerald);
        border-color: rgba(16, 185, 129, 0.3);
    }
    
    .cyan-glow:hover {
        box-shadow: var(--glow-cyan);
        border-color: rgba(6, 182, 212, 0.3);
    }

    /* Fact Ticker */
    .fact-ticker {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: rgba(99, 102, 241, 0.05);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 12px;
        padding: 10px 16px;
        margin-bottom: 1.5rem;
        font-size: 0.88rem;
    }
    
    .ticker-lbl {
        font-weight: 700;
        color: var(--primary);
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        flex-shrink: 0;
    }
    
    .ticker-val {
        color: var(--text-secondary);
        font-weight: 500;
    }

    /* Scanner laser visual effects */
    .scanner-preview-wrapper {
        position: relative;
        width: 100%;
        max-height: 400px;
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        justify-content: center;
        align-items: center;
        background: #000;
    }
    
    .scan-preview-img {
        width: 100%;
        height: auto;
        max-height: 400px;
        object-fit: contain;
        display: block;
        opacity: 0.75;
    }
    
    .scanner-laser {
        position: absolute;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--secondary), var(--primary), var(--secondary), transparent);
        box-shadow: 0 0 12px var(--secondary), 0 0 20px var(--primary);
        animation: scan-sweep 3s infinite linear;
        z-index: 2;
    }
    
    .scan-overlay-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--secondary);
        text-shadow: 0 0 10px rgba(6, 182, 212, 0.8);
        letter-spacing: 0.15em;
        animation: pulse-hud 1.5s infinite ease-in-out;
        pointer-events: none;
        z-index: 3;
    }
    
    @keyframes scan-sweep {
        0%, 100% { top: 0%; }
        50% { top: 100%; }
    }

    .scanner-preview-wrapper.scan-success {
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    .scan-success-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        background: rgba(16, 185, 129, 0.85);
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.05em;
        box-shadow: var(--glow-emerald);
        z-index: 2;
    }

    /* Operator Manual Pipeline Diagram */
    .manual-pipeline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 2rem;
        margin-top: 1rem;
        margin-bottom: 2rem;
        overflow-x: auto;
    }
    
    .pipeline-node {
        flex: 1;
        background: rgba(18, 20, 32, 0.8);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 8px;
        min-width: 160px;
        transition: all 0.3s ease;
    }
    
    .pipeline-node:hover {
        transform: translateY(-4px);
    }
    
    .pipeline-node.indigo-glow:hover {
        box-shadow: var(--glow-indigo);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    .pipeline-node.cyan-glow:hover {
        box-shadow: var(--glow-cyan);
        border-color: rgba(6, 182, 212, 0.3);
    }
    
    .pipeline-node.emerald-glow:hover {
        box-shadow: var(--glow-emerald);
        border-color: rgba(16, 185, 129, 0.3);
    }
    
    .pipeline-node.yellow-glow:hover {
        box-shadow: 0 0 25px rgba(234, 179, 8, 0.15);
        border-color: rgba(234, 179, 8, 0.3);
    }
    
    .pipeline-node .icon {
        font-size: 1.8rem;
    }
    
    .pipeline-node .lbl {
        font-weight: 700;
        font-size: 1rem;
        color: var(--text-primary);
    }
    
    .pipeline-node .desc {
        font-size: 0.78rem;
        color: var(--text-secondary);
        line-height: 1.3;
    }
    
    .pipeline-arrow {
        font-size: 1.5rem;
        color: var(--text-muted);
        user-select: none;
    }
    
    .manual-layout {
        display: flex;
        flex-direction: column;
        gap: 2rem;
        max-width: 1200px;
        width: 100%;
        margin: 0 auto;
        box-sizing: border-box;
    }
    
    .manual-section h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .section-subtitle {
        margin: 0;
        font-size: 0.95rem;
        color: var(--text-secondary);
    }
    
    .double-col {
        grid-template-columns: 1.1fr 0.9fr;
    }
    
    .flex-col {
        display: flex;
        flex-direction: column;
    }
    
    .gap-md {
        gap: 1.5rem;
    }
    
    .glass-card.compact {
        padding: 1.8rem;
    }
    
    .glass-card.compact h3 {
        margin: 0 0 0.75rem 0;
        font-size: 1.25rem;
    }
    
    .desc-text {
        font-size: 0.95rem;
        color: var(--text-secondary);
        line-height: 1.5;
        margin: 0 0 1.25rem 0;
    }
    
    .tech-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.2rem;
    }
    
    @media (max-width: 600px) {
        .tech-grid {
            grid-template-columns: 1fr;
        }
    }
    
    .tech-card {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem;
    }
    
    .tech-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--secondary);
        display: block;
        margin-bottom: 6px;
    }
    
    .tech-card p {
        margin: 0;
        font-size: 0.8rem;
        color: var(--text-secondary);
        line-height: 1.4;
    }
    
    .operator-instructions-card h3 {
        margin: 0 0 1.2rem 0;
        font-size: 1.35rem;
    }
    
    .instructions-list {
        display: flex;
        flex-direction: column;
        gap: 1.2rem;
    }
    
    .instruction-item {
        border-left: 2px solid var(--primary);
        padding-left: 1rem;
    }
    
    .instruction-item .item-head {
        font-weight: 700;
        font-size: 0.95rem;
        color: var(--text-primary);
        display: block;
        margin-bottom: 4px;
    }
    
    .instruction-item p {
        margin: 0;
        font-size: 0.85rem;
        color: var(--text-secondary);
        line-height: 1.4;
    }

    /* Specimen Action Suite styling */
    .hud-study-actions {
        background: rgba(99, 102, 241, 0.03);
        border: 1px solid rgba(99, 102, 241, 0.1);
        border-radius: 16px;
        padding: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .hud-study-actions.border-top {
        margin-top: 2rem;
        border-top: 1px solid var(--border);
        padding-top: 1.5rem;
    }
    
    .hud-study-actions h4 {
        margin: 0 0 12px 0;
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--secondary);
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    .study-actions-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
    }
    
    @media (max-width: 480px) {
        .study-actions-grid {
            grid-template-columns: 1fr;
        }
    }
    
    .hud-study-actions .action-btn {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border);
        color: var(--text-secondary);
        padding: 10px 14px;
        border-radius: 10px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }
    
    .hud-study-actions .action-btn:hover {
        background: rgba(99, 102, 241, 0.08);
        border-color: rgba(99, 102, 241, 0.25);
        color: #f1f5f9;
        transform: translateY(-1px);
        box-shadow: var(--glow-indigo);
    }
    
    .hud-study-actions .action-btn.compare-btn:hover {
        background: rgba(6, 182, 212, 0.08);
        border-color: rgba(6, 182, 212, 0.25);
        color: #f1f5f9;
        box-shadow: var(--glow-cyan);
    }

    /* Scanner step telemetry/badges styling */
    .status-pill {
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.05em;
    }
    
    .status-success {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: var(--accent);
    }
    
    .status-info {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.2);
        color: var(--primary);
    }
    
    .status-loading {
        background: rgba(6, 182, 212, 0.08);
        border: 1px solid rgba(6, 182, 212, 0.2);
        color: var(--secondary);
    }
    
    .status-compiling {
        background: rgba(168, 85, 247, 0.08);
        border: 1px solid rgba(168, 85, 247, 0.2);
        color: #a855f7;
    }
    
    .status-ready {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: var(--accent);
    }

    .discovery-step-view {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        text-align: center;
        gap: 1.5rem;
        background: rgba(0, 0, 0, 0.1);
        border: 1px dashed var(--border);
        border-radius: 20px;
    }

    .discovery-pulse-container {
        position: relative;
        width: 64px;
        height: 64px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .pulse-icon {
        font-size: 2.2rem;
        z-index: 2;
    }

    .pulse-waves {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: rgba(6, 182, 212, 0.15);
        animation: pulse-ring 1.8s cubic-bezier(0.215, 0.610, 0.355, 1) infinite;
        z-index: 1;
    }

    @keyframes pulse-ring {
        0% { transform: scale(0.65); opacity: 1; }
        100% { transform: scale(1.6); opacity: 0; }
    }

    .discovery-loading-spinner {
        width: 50px;
        height: 50px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .spinner-core {
        width: 36px;
        height: 36px;
        border: 3px solid rgba(6, 182, 212, 0.1);
        border-top-color: var(--secondary);
        border-radius: 50%;
        animation: spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }

    .discovery-text {
        font-size: 0.95rem;
        color: var(--text-secondary);
        max-width: 320px;
        line-height: 1.5;
        margin: 0;
    }

    .active-pulse {
        animation: active-pulse-btn 2s infinite ease-in-out;
    }

    @keyframes active-pulse-btn {
        0%, 100% { box-shadow: 0 0 10px rgba(99, 102, 241, 0.2); }
        50% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.45); }
    }

    /* Global polish micro-interactions */
    button, .action-btn, .ctrl-btn, .nav-item {
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    button:hover:not(:disabled), .action-btn:hover, .ctrl-btn:hover {
        transform: translateY(-2px);
    }
    
    button:active:not(:disabled), .action-btn:active, .ctrl-btn:active {
        transform: translateY(1px);
    }

    .glass-card {
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.12);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
    }

    /* Success pop-in scaling badge */
    .scan-success-badge {
        animation: pop-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    }
    
    @keyframes pop-in {
        0% { transform: scale(0.6); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }

    /* slide-up content reveal */
    .slide-up-reveal {
        opacity: 0;
        transform: translateY(12px);
        animation: slideUpIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    
    @keyframes slideUpIn {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Pulse animation around scan border wrapper */
    .scanner-preview-wrapper::after {
        content: '';
        position: absolute;
        inset: 0;
        border: 2px solid var(--secondary);
        border-radius: 12px;
        animation: scan-border-pulse 2s infinite ease-in-out;
        pointer-events: none;
        opacity: 0.3;
    }
    
    @keyframes scan-border-pulse {
        0%, 100% { transform: scale(1); opacity: 0.3; }
        50% { transform: scale(1.015); opacity: 0.6; }
    }
</style>
