let pdfDoc = null;
let currentPdfUrl = null;

// Initialize pdf.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

async function openPdfViewer(filename, pageNumber, snippet) {
    const pdfPane = document.getElementById('pdf-pane');
    const chatContainer = document.querySelector('.chat-container');
    const pdfContainer = document.getElementById('pdf-render-container');
    const pdfHeaderTitle = document.getElementById('pdf-header-title');
    
    // Show pane
    pdfPane.classList.add('open');
    document.getElementById('pdf-resizer').classList.add('open');
    chatContainer.classList.add('split');
    
    pdfHeaderTitle.innerText = `${filename} (Page ${pageNumber})`;
    
    const url = `${API_URL}/files/papers/${encodeURIComponent(filename)}`;
    
    if (currentPdfUrl !== url) {
        pdfContainer.innerHTML = '<div class="pdf-loading"><div class="spinner"></div><p style="margin-top:10px;">Loading Document...</p></div>';
        try {
            const loadingTask = pdfjsLib.getDocument(url);
            pdfDoc = await loadingTask.promise;
            currentPdfUrl = url;
        } catch (e) {
            pdfContainer.innerHTML = `<div class="pdf-error" style="color:var(--danger); text-align:center; padding:20px;">Failed to load PDF:<br>${e.message}</div>`;
            return;
        }
    }
    
    await renderPage(pageNumber, snippet);
}

async function renderPage(pageNum, snippet) {
    const pdfContainer = document.getElementById('pdf-render-container');
    pdfContainer.innerHTML = '<div class="pdf-loading"><div class="spinner"></div><p style="margin-top:10px;">Rendering Page...</p></div>';
    
    try {
        const page = await pdfDoc.getPage(pageNum);
        
        // Calculate scale to fit width
        const unscaledViewport = page.getViewport({ scale: 1.0 });
        const containerWidth = pdfContainer.clientWidth - 40; // padding
        const scale = containerWidth / unscaledViewport.width;
        
        const viewport = page.getViewport({ scale: Math.max(scale, 1.0) });
        
        pdfContainer.innerHTML = '';
        pdfContainer.style.position = 'relative';
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        canvas.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        canvas.style.borderRadius = '4px';
        
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
        pdfContainer.appendChild(canvas);
        
        if (snippet) {
            const textContent = await page.getTextContent();
            highlightText(textContent, viewport, snippet, pdfContainer);
        }
        
    } catch (e) {
        pdfContainer.innerHTML = `<div class="pdf-error" style="color:var(--danger); text-align:center; padding:20px;">Error rendering page:<br>${e.message}</div>`;
    }
}

function highlightText(textContent, viewport, snippet, container) {
    // Clean snippet
    const snippetStr = snippet.replace(/[\r\n]+/g, ' ');
    const words = snippetStr.replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length > 4);
    
    if (words.length === 0) return;
    
    let bestMatchItems = [];
    let maxMatches = 0;
    
    for (let i = 0; i < textContent.items.length; i++) {
        const item = textContent.items[i];
        let matches = 0;
        
        for (const word of words) {
            if (item.str.toLowerCase().includes(word.toLowerCase())) {
                matches++;
            }
        }
        
        if (matches > 0 && matches > maxMatches) {
            maxMatches = matches;
            bestMatchItems = [item];
            
            // Expand context
            if (i > 0) bestMatchItems.push(textContent.items[i-1]);
            if (i < textContent.items.length - 1) bestMatchItems.push(textContent.items[i+1]);
        }
    }
    
    if (bestMatchItems.length > 0) {
        bestMatchItems.forEach(item => {
            if (!item.str.trim()) return;
            
            const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
            const height = Math.abs(item.transform[3]) * viewport.scale;
            const width = item.width * viewport.scale;
            const x = tx[4];
            const y = tx[5] - height; 
            
            const highlightDiv = document.createElement('div');
            highlightDiv.className = 'pdf-highlight';
            highlightDiv.style.position = 'absolute';
            highlightDiv.style.left = `${x}px`;
            highlightDiv.style.top = `${y}px`;
            highlightDiv.style.width = `${width}px`;
            highlightDiv.style.height = `${height * 1.3}px`;
            highlightDiv.style.backgroundColor = 'rgba(255, 226, 80, 0.4)';
            highlightDiv.style.borderBottom = '2px solid rgba(255, 193, 7, 0.8)';
            highlightDiv.style.pointerEvents = 'none';
            
            container.appendChild(highlightDiv);
        });
        
        setTimeout(() => {
            const highlights = container.querySelectorAll('.pdf-highlight');
            if (highlights.length > 0) {
                highlights[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 300);
    }
}

function closePdfViewer() {
    const pdfPane = document.getElementById('pdf-pane');
    const chatContainer = document.querySelector('.chat-container');
    pdfPane.classList.remove('open');
    document.getElementById('pdf-resizer').classList.remove('open');
    pdfPane.style.width = '';

    chatContainer.classList.remove('split');
}

// Resizer Logic
document.addEventListener("DOMContentLoaded", () => {
    const resizer = document.getElementById('pdf-resizer');
    const pdfPane = document.getElementById('pdf-pane');
    let isDragging = false;

    resizer.addEventListener('mousedown', (e) => {
        isDragging = true;
        document.body.classList.add('is-dragging');
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        // Window width minus mouse X gives the width of the right pane
        let newWidth = window.innerWidth - e.clientX;
        
        // Set constraints
        if (newWidth < 300) newWidth = 300;
        const maxAllowed = window.innerWidth - 400; // Leave 400px for sidebar and chat
        if (newWidth > maxAllowed) newWidth = maxAllowed;
        
        pdfPane.style.width = newWidth + 'px';
        
        // The canvas inside might need to re-scale, but it will do so when next page is loaded.
        // For smooth resizing, we could re-render, but usually it's fine as is.
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            document.body.classList.remove('is-dragging');
        }
    });
});
