class InteractiveCanvas {
    constructor(containerId,
        imageUrl,
        structures,
        initialRectangles = null,
        maskUrl = null,
        initialEndpoints = null,
        clearLocalStorage = false
    ) {
        this.container = document.getElementById(containerId);
        this.allStructures = structures;
        this.usedStructures = new Set();
        this.currentStructure = structures[0];
        this.rectangles = [];
        this.isDrawing = false;
        this.selectedRect = null;
        this.dragMode = 'none';
        this.maskUrl = maskUrl;
        
        // TN measurement properties
        this.mode = 'bounding_box'; // 'bounding_box' or 'tn_measurement'
        this.endpoints = [];
        this.tempEndpoint = null;
        this.isPlacingEndpoint = false;
        this.previewLine = null;
        
        // Define class colors
        this.classColors = {
            "Cisternae Magna": "#FF5733",
            "Intracranial Translucency": "#33FF57",
            "Nuchal Translucency": "#3357FF",
            "Midbrain": "#F1C40F",
            "Nasal Bone": "#8E44AD",
            "Nasal Skin": "#E67E22",
            "Nasal Tip": "#2ECC71",
            "Palate": "#3498DB",
            "Thalami": "#E74C3C"
        };
        
        // Handle localStorage clearing first
        if (clearLocalStorage) {
            this.clearLocalStorage();
        }
        
        // BLOCKING CALL: Save provided data to localStorage if provided
        if (initialRectangles !== null) {
            this.saveRectanglesToLocalStorage(initialRectangles);
        }
        
        if (initialEndpoints !== null) {
            this.saveEndpointsToLocalStorage(initialEndpoints);
        }
        
        // ALWAYS read from localStorage to build the component
        const cachedData = this.loadFromLocalStorage();
        const rectanglesToLoad = cachedData.rectangles || [];
        const endpointsToLoad = cachedData.endpoints || [];
        
        this.setupCanvas(imageUrl);
        this.setupControls();
        this.bindEvents();
        
        // Load rectangles if available
        if (rectanglesToLoad && rectanglesToLoad.length > 0) {
            this.pendingInitialRectangles = rectanglesToLoad;
        }
        
        // Load endpoints if available
        if (endpointsToLoad && endpointsToLoad.length > 0) {
            this.endpoints = endpointsToLoad.map(ep => ({ x: ep.x, y: ep.y }));
        }
        
        // Update dropdown after everything is set up
        this.updateDropdown();
    }

    saveRectanglesToLocalStorage(rectangles) {
        try {
            // Get existing data
            const existingData = this.loadFromLocalStorage();
            
            // Update with new rectangles
            const newData = {
                ...existingData,
                rectangles: rectangles
            };
            
            // Save synchronously
            localStorage.setItem('streamlit_annotations', JSON.stringify(newData));
            console.log('Saved rectangles to localStorage:', rectangles);
        } catch (error) {
            console.error('Error saving rectangles to localStorage:', error);
        }
    }

    saveEndpointsToLocalStorage(endpoints) {
        try {
            // Get existing data
            const existingData = this.loadFromLocalStorage();
            
            // Update with new endpoints
            const newData = {
                ...existingData,
                endpoints: endpoints
            };
            
            // Save synchronously
            localStorage.setItem('streamlit_annotations', JSON.stringify(newData));
            console.log('Saved endpoints to localStorage:', endpoints);
        } catch (error) {
            console.error('Error saving endpoints to localStorage:', error);
        }
    }

    setupCanvas(imageUrl) {
        // Create main container
        this.container.innerHTML = `
            <div id="canvas-controls" style="margin-bottom: 10px; padding: 12px; background: #0e1117; border-radius: 8px;">
                <div style="margin-bottom: 10px;">
                    <label style="color: #fafafa; font-family: 'Source Sans Pro', sans-serif; font-weight: 600; margin-right: 10px;">Mode:</label>
                    <select id="mode-select" style="
                        margin-right: 10px; 
                        padding: 8px 12px; 
                        background: #262730; 
                        color: #fafafa; 
                        border: 1px solid #555; 
                        border-radius: 4px;
                        font-family: 'Source Sans Pro', sans-serif;
                    ">
                        <option value="bounding_box">Draw Bounding Boxes</option>
                        <option value="tn_measurement">Measure TN</option>
                    </select>
                </div>
                <div id="bounding-box-controls">
                    <select id="structure-select" style="
                        margin-right: 10px; 
                        padding: 8px 12px; 
                        background: #262730; 
                        color: #fafafa; 
                        border: 1px solid #555; 
                        border-radius: 4px;
                        font-family: 'Source Sans Pro', sans-serif;
                    ">
                    </select>
                    <button id="clear-all" style="
                        padding: 8px 16px;
                        background: #ff4b4b;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-family: 'Source Sans Pro', sans-serif;
                        font-weight: 600;
                        transition: all 0.2s;
                        margin-right: 10px;
                    " onmouseover="if(!this.disabled) this.style.background='#ff6b6b'" onmouseout="if(!this.disabled) this.style.background='#ff4b4b'">Clear All</button>
                </div>
                <div id="tn-controls" style="display: none;">
                    <div style="margin-bottom: 10px;">
                        <span style="color: #fafafa; font-family: 'Source Sans Pro', sans-serif; margin-right: 10px;">
                            <span id="tn-status">Click to place first endpoint</span>
                        </span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <label style="color: #fafafa; font-family: 'Source Sans Pro', sans-serif; margin-right: 10px;">
                            Pixel to mm ratio:
                        </label>
                        <input id="pixel-mm-ratio" type="number" min="0.01" max="10" step="0.01" value="0.18" style="
                            padding: 6px 10px;
                            background: #262730;
                            color: #fafafa;
                            border: 1px solid #555;
                            border-radius: 4px;
                            font-family: 'Source Sans Pro', sans-serif;
                            width: 80px;
                            margin-right: 10px;
                        ">
                        <span style="color: #888; font-family: 'Source Sans Pro', sans-serif; font-size: 12px;">
                            mm/pixel
                        </span>
                    </div>
                    <div id="tn-measurement" style="margin-bottom: 10px; display: none;">
                        <div style="color: #fafafa; font-family: 'Source Sans Pro', sans-serif; font-size: 14px;">
                            <div style="margin-bottom: 5px;">
                                <strong>TN Distance:</strong> 
                                <span id="tn-distance-mm" style="color: #00ff00; font-weight: bold;">0.00 mm</span>
                            </div>
                            <div style="color: #888; font-size: 12px;">
                                (<span id="tn-distance-pixels">0.00 pixels</span>)
                            </div>
                        </div>
                    </div>
                    <button id="clear-tn" style="
                        padding: 8px 16px;
                        background: #ff4b4b;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-family: 'Source Sans Pro', sans-serif;
                        font-weight: 600;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='#ff6b6b'" onmouseout="this.style.background='#ff4b4b'">Clear TN</button>
                </div>
            </div>
            <div id="canvas-container" style="position: relative; display: inline-block; border: 2px solid #262730; border-radius: 8px; overflow: hidden;">
                <canvas id="composite-canvas" style="display: block; max-width: 100%;"></canvas>
                <svg id="annotation-svg" style="position: absolute; top: 0; left: 0; pointer-events: all;"></svg>
            </div>
        `;
        
        this.canvas = document.getElementById('composite-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.svg = document.getElementById('annotation-svg');
        
        // Load and composite the images
        this.loadAndCompositeImages(imageUrl);
    }

    loadAndCompositeImages(imageUrl) {
        this.baseImage = new Image();
        this.baseImage.crossOrigin = 'anonymous';
        
        this.baseImage.onload = () => {
            // Set canvas dimensions
            this.canvas.width = this.baseImage.width;
            this.canvas.height = this.baseImage.height;
            
            // Set SVG dimensions
            this.svg.setAttribute('width', this.canvas.width);
            this.svg.setAttribute('height', this.canvas.height);
            
            // Draw the composite image
            this.drawComposite();
            
            // Load initial rectangles and endpoints after image is loaded
            if (this.pendingInitialRectangles && this.pendingInitialRectangles.length > 0) {
                this.createInitialRectangles(this.pendingInitialRectangles);
                this.pendingInitialRectangles = null;
            }
            
            if (this.endpoints && this.endpoints.length > 0) {
                this.createEndpointCrosses();
                this.updateTNStatus();
            }
        };
        
        this.baseImage.src = imageUrl;
    }

    clearLocalStorage() {
        try {
            localStorage.removeItem('streamlit_annotations');
            console.log('Cleared localStorage annotations');
        } catch (error) {
            console.error('Error clearing localStorage:', error);
        }
    }

    loadFromLocalStorage() {
        try {
            const storedData = localStorage.getItem('streamlit_annotations');
            if (storedData) {
                const data = JSON.parse(storedData);
                console.log('Loaded annotations from localStorage:', data);
                
                // Restore pixel-mm ratio if available
                if (data.pixelMmRatio && this.pixelMmRatio) {
                    this.pixelMmRatio.value = data.pixelMmRatio;
                }
                
                if (data.rectangles) {
                    data.rectangles.forEach(rect => {
                        this.usedStructures.add(rect.label);
                    });
                }
                
                return {
                    rectangles: data.rectangles || [],
                    endpoints: data.endpoints || [],
                    pixelMmRatio: data.pixelMmRatio || 0.18
                };
            }
        } catch (error) {
            console.error('Error loading from localStorage:', error);
        }
        
        return {
            rectangles: [],
            endpoints: [],
            pixelMmRatio: 0.18
        };
    }

    drawComposite() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Convert grayscale image to RGB
        this.ctx.drawImage(this.baseImage, 0, 0);
        
        // If mask is available, overlay it
        if (this.maskUrl) {
            this.maskImage = new Image();
            this.maskImage.crossOrigin = 'anonymous';
            
            this.maskImage.onload = () => {
                this.overlayMask();
            };
            
            this.maskImage.src = this.maskUrl;
        }
    }

    overlayMask() {
       // Create a temporary canvas for mask processing
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = this.maskImage.width;
        tempCanvas.height = this.maskImage.height;
        
        // Draw mask to temporary canvas
        tempCtx.drawImage(this.maskImage, 0, 0);
        
        // Get mask image data
        const maskImageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        const maskData = maskImageData.data;
        
        // Create colored overlay
        const overlayCanvas = document.createElement('canvas');
        const overlayCtx = overlayCanvas.getContext('2d');
        overlayCanvas.width = this.canvas.width;
        overlayCanvas.height = this.canvas.height;
        
        // Get Nuchal Translucency color
        const ntColor = this.classColors["Nuchal Translucency"];
        const rgb = this.hexToRgb(ntColor);
        
        // Create overlay image data
        const overlayImageData = overlayCtx.createImageData(overlayCanvas.width, overlayCanvas.height);
        const overlayData = overlayImageData.data;
        
        // Scale mask to match canvas size if needed
        const scaleX = tempCanvas.width / overlayCanvas.width;
        const scaleY = tempCanvas.height / overlayCanvas.height;
        
        for (let y = 0; y < overlayCanvas.height; y++) {
            for (let x = 0; x < overlayCanvas.width; x++) {
                const maskX = Math.floor(x * scaleX);
                const maskY = Math.floor(y * scaleY);
                const maskIndex = (maskY * tempCanvas.width + maskX) * 4;
                const overlayIndex = (y * overlayCanvas.width + x) * 4;
                
                // Check bounds to prevent accessing undefined array elements
                if (maskIndex >= 0 && maskIndex < maskData.length) {
                    // For binary mask, check if any channel (R, G, or B) is > 128
                    // Since it's binary (0 or 1), we need to check the actual pixel value
                    const maskValue = maskData[maskIndex]; // Red channel
                    
                    // Binary mask: 0 = background, >0 = foreground
                    if (maskValue > 128) { // Threshold for binary mask
                        // Apply colored overlay with alpha
                        overlayData[overlayIndex] = rgb.r;     // Red
                        overlayData[overlayIndex + 1] = rgb.g; // Green  
                        overlayData[overlayIndex + 2] = rgb.b; // Blue
                        overlayData[overlayIndex + 3] = 128;   // Alpha (50% opacity)
                    } else {
                        overlayData[overlayIndex + 3] = 0;     // Transparent
                    }
                } else {
                    overlayData[overlayIndex + 3] = 0;         // Transparent for out-of-bounds
                }
            }
        }
        
        // Draw the colored overlay
        overlayCtx.putImageData(overlayImageData, 0, 0);
        
        // Composite the overlay onto the main canvas
        this.ctx.globalCompositeOperation = 'source-over';
        this.ctx.drawImage(overlayCanvas, 0, 0);
        
        // Reset composite operation
        this.ctx.globalCompositeOperation = 'source-over';
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    setupControls() {
        this.modeSelect = document.getElementById('mode-select');
        this.structureSelect = document.getElementById('structure-select');
        this.clearAllBtn = document.getElementById('clear-all');
        this.clearTnBtn = document.getElementById('clear-tn');
        this.tnStatus = document.getElementById('tn-status');
        this.boundingBoxControls = document.getElementById('bounding-box-controls');
        this.tnControls = document.getElementById('tn-controls');
        this.pixelMmRatio = document.getElementById('pixel-mm-ratio');
        this.tnMeasurement = document.getElementById('tn-measurement');
        this.tnDistanceMm = document.getElementById('tn-distance-mm');
        this.tnDistancePixels = document.getElementById('tn-distance-pixels');
        
        this.modeSelect.addEventListener('change', (e) => {
            this.mode = e.target.value;
            this.updateModeUI();
        });
        
        this.structureSelect.addEventListener('change', (e) => {
            this.currentStructure = e.target.value;
        });
        
        this.clearAllBtn.addEventListener('click', () => {
            if (!this.clearAllBtn.disabled) {
                this.clearAll();
            }
        });
        
        this.clearTnBtn.addEventListener('click', () => {
            this.clearTN();
        });
        
        // Add event listener for pixel-mm ratio changes
        this.pixelMmRatio.addEventListener('input', () => {
            this.updateTNMeasurement();
        });
    }

    updateModeUI() {
        if (this.mode === 'bounding_box') {
            this.boundingBoxControls.style.display = 'block';
            this.tnControls.style.display = 'none';
            this.svg.style.cursor = 'crosshair';
        } else {
            this.boundingBoxControls.style.display = 'none';
            this.tnControls.style.display = 'block';
            this.svg.style.cursor = 'crosshair';
            this.updateTNStatus();
        }
    }

    updateTNStatus() {
        if (this.endpoints.length === 0) {
            this.tnStatus.textContent = 'Click to place first endpoint';
            this.tnMeasurement.style.display = 'none';
        } else if (this.endpoints.length === 1) {
            this.tnStatus.textContent = 'Click to place second endpoint';
            this.tnMeasurement.style.display = 'none';
        } else {
            this.tnStatus.textContent = 'TN measurement complete';
            this.tnMeasurement.style.display = 'block';
            this.updateTNMeasurement();
        }
    }

    updateTNMeasurement() {
        if (this.endpoints.length !== 2) return;
        
        // Calculate distance in pixels
        const dx = this.endpoints[1].x - this.endpoints[0].x;
        const dy = this.endpoints[1].y - this.endpoints[0].y;
        const distancePixels = Math.sqrt(dx * dx + dy * dy);
        
        // Get pixel-to-mm ratio
        const pixelMmRatio = parseFloat(this.pixelMmRatio.value) || 0.18;
        
        // Calculate distance in mm
        const distanceMm = distancePixels * pixelMmRatio;
        
        // Update display
        this.tnDistancePixels.textContent = `${distancePixels.toFixed(2)} pixels`;
        this.tnDistanceMm.textContent = `${distanceMm.toFixed(2)} mm`;
    }


    updateDropdown() {
        console.log('Used structures:', this.usedStructures);
        const availableStructures = this.allStructures.filter(structure => !this.usedStructures.has(structure));
        console.log('Available structures:', availableStructures);
        
        // Update the select dropdown
        const select = document.getElementById('structure-select');
        if (select) {
            if (availableStructures.length > 0) {
                select.innerHTML = availableStructures.map(s => `<option value="${s}">${s}</option>`).join('');
                select.disabled = false;
                this.currentStructure = availableStructures[0];
            } else {
                select.innerHTML = '<option>All structures annotated</option>';
                select.disabled = true;
                this.currentStructure = null;
            }
        }
        
        // Update clear button state
        const clearBtn = document.getElementById('clear-all');
        if (clearBtn) {
            // Button should be disabled when there are NO rectangles to clear
            const shouldDisable = this.rectangles.length === 0;
            clearBtn.disabled = shouldDisable;
            clearBtn.style.opacity = shouldDisable ? '0.5' : '1';
            clearBtn.style.cursor = shouldDisable ? 'not-allowed' : 'pointer';
        }
    }

    getColorForLabel(label) {
        return this.classColors[label] || "#FF0000";
    }

    createInitialRectangles(initialRectangles) {
        initialRectangles.forEach(rectData => {
            const rect = {
                id: 'rect_' + Date.now() + '_' + Math.random(),
                x: rectData.x,
                y: rectData.y,
                width: rectData.width,
                height: rectData.height,
                label: rectData.label,
                color: rectData.color || this.getColorForLabel(rectData.label),
                timestamp: rectData.timestamp || new Date().toISOString()
            };
            
            const svgRect = this.createSVGRectangle(rect);
            rect.element = svgRect;
            
            this.rectangles.push(rect);
            this.usedStructures.add(rect.label);
            
            // Force update the rectangle display to ensure labels are positioned correctly
            this.updateRectangle(rect, rect.x, rect.y, rect.x + rect.width, rect.y + rect.height);
        });

        this.autoSaveAnnotations();
    }

    loadInitialRectangles(initialRectangles) {
    // Wait for base image to be loaded before creating rectangles
        if (this.baseImage && this.baseImage.complete) {
            this.createInitialRectangles(initialRectangles);
        } else if (this.baseImage) {
            // Add event listener to create rectangles once image loads
            this.baseImage.addEventListener('load', () => {
                this.createInitialRectangles(initialRectangles);
            });
        } else {
            // If baseImage doesn't exist yet, wait a bit and try again
            setTimeout(() => {
                this.loadInitialRectangles(initialRectangles);
            }, 100);
        }
    }
    
    bindEvents() {
        this.svg.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.svg.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.svg.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.svg.addEventListener('click', (e) => this.handleClick(e));
    }
    
    getMousePos(e) {
        const rect = this.svg.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    handleClick(e) {
        e.stopPropagation();
    }
    
     handleMouseDown(e) {
        if (this.mode === 'tn_measurement') {
            this.handleTNClick(e);
            return;
        }
        
        // Original bounding box logic
        const pos = this.getMousePos(e);
        const clickedRect = this.findRectangleAt(pos.x, pos.y);
        
        if (clickedRect) {
            this.selectedRect = clickedRect;
            this.dragMode = this.getDragMode(clickedRect, pos.x, pos.y);
            this.startDrag = pos;
            this.startRect = { ...clickedRect };
        } else if (this.currentStructure) {
            this.isDrawing = true;
            this.startDrag = pos;
            this.createNewRectangle(pos.x, pos.y);
        }
        
        e.preventDefault();
    }

    handleTNClick(e) {
        // Don't place new endpoints if clicking on an existing cross
        const target = e.target;
        if (target.closest('.endpoint-cross')) {
            return; // Let the drag handler take over
        }
        
        const pos = this.getMousePos(e);
        
        if (this.endpoints.length < 2) {
            this.endpoints.push({ x: pos.x, y: pos.y });
            this.createEndpointCross(pos.x, pos.y, this.endpoints.length - 1);
            
            if (this.endpoints.length === 2) {
                this.createEndpointLine();
                this.clearPreviewLine();
            }
            
            this.updateTNStatus();
            this.autoSaveAnnotations();
        }
        
        e.preventDefault();
    }
    
    handleMouseMove(e) {
        if (this.mode === 'tn_measurement' && this.endpoints.length === 1) {
            this.updatePreviewLine(e);
            return;
        }
        
        if (this.mode === 'bounding_box') {
            // Original bounding box logic
            const pos = this.getMousePos(e);
            
            if (this.isDrawing && this.rectangles.length > 0) {
                const currentRect = this.rectangles[this.rectangles.length - 1];
                this.updateRectangle(currentRect, this.startDrag.x, this.startDrag.y, pos.x, pos.y);
            } else if (this.selectedRect && this.dragMode !== 'none') {
                this.handleDragResize(pos);
            } else {
                this.updateCursor(pos);
            }
        }
    }

    updatePreviewLine(e) {
        if (this.endpoints.length !== 1) return;
        
        const pos = this.getMousePos(e);
        const startPoint = this.endpoints[0];
        
        // Remove existing preview line
        this.clearPreviewLine();
        
        // Create new preview line
        this.previewLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        this.previewLine.setAttribute('x1', startPoint.x);
        this.previewLine.setAttribute('y1', startPoint.y);
        this.previewLine.setAttribute('x2', pos.x);
        this.previewLine.setAttribute('y2', pos.y);
        this.previewLine.setAttribute('stroke', '#FFFF00'); // Same color as crosses
        this.previewLine.setAttribute('stroke-width', '2');
        this.previewLine.setAttribute('stroke-dasharray', '5,5');
        this.previewLine.setAttribute('opacity', '0.7');
        
        this.svg.appendChild(this.previewLine);
    }

    clearPreviewLine() {
        if (this.previewLine) {
            this.previewLine.remove();
            this.previewLine = null;
        }
    }

    createEndpointCross(x, y, index) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'endpoint-cross');
        g.setAttribute('data-index', index); // Store index for reference
        
        const size = 8;
        const strokeWidth = 3;
        const color = '#FFFF00'; // Bright yellow for high contrast
        
        // Create two lines forming an X
        const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line1.setAttribute('x1', x - size);
        line1.setAttribute('y1', y - size);
        line1.setAttribute('x2', x + size);
        line1.setAttribute('y2', y + size);
        line1.setAttribute('stroke', color);
        line1.setAttribute('stroke-width', strokeWidth);
        line1.setAttribute('stroke-linecap', 'round');
        
        const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line2.setAttribute('x1', x - size);
        line2.setAttribute('y1', y + size);
        line2.setAttribute('x2', x + size);
        line2.setAttribute('y2', y - size);
        line2.setAttribute('stroke', color);
        line2.setAttribute('stroke-width', strokeWidth);
        line2.setAttribute('stroke-linecap', 'round');
        
        g.appendChild(line1);
        g.appendChild(line2);
        
        // Make the cross draggable
        g.style.cursor = 'move';
        g.setAttribute('draggable', 'false'); // Prevent HTML5 drag
        
        // Add mouse event listeners for dragging
        let isDragging = false;
        let dragStartPos = null;
        let originalPos = null;
        
        g.addEventListener('mousedown', (e) => {
            if (this.mode !== 'tn_measurement') return;
            
            e.stopPropagation();
            e.preventDefault();
            
            isDragging = true;
            dragStartPos = this.getMousePos(e);
            originalPos = { x: this.endpoints[index].x, y: this.endpoints[index].y };
            
            g.style.cursor = 'grabbing';
            
            // Add global mouse events
            const handleMouseMove = (e) => {
                if (!isDragging) return;
                
                const currentPos = this.getMousePos(e);
                const dx = currentPos.x - dragStartPos.x;
                const dy = currentPos.y - dragStartPos.y;
                
                // Update endpoint position
                this.endpoints[index].x = originalPos.x + dx;
                this.endpoints[index].y = originalPos.y + dy;
                
                // Update visual position of the cross
                this.updateEndpointCrossPosition(g, this.endpoints[index].x, this.endpoints[index].y);
                
                // Update the line if both endpoints exist
                if (this.endpoints.length === 2) {
                    this.updateEndpointLine();
                    this.updateTNMeasurement();
                }
                
                e.preventDefault();
            };
            
            const handleMouseUp = (e) => {
                if (isDragging) {
                    isDragging = false;
                    g.style.cursor = 'move';
                    
                    // Auto-save the new position
                    this.autoSaveAnnotations();
                    this.updateTNMeasurement();
                    
                    // Remove global event listeners
                    document.removeEventListener('mousemove', handleMouseMove);
                    document.removeEventListener('mouseup', handleMouseUp);
                    
                    e.preventDefault();
                }
            };
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
        
        this.svg.appendChild(g);
        
        // Store reference
        this.endpoints[index].element = g;
        this.endpoints[index].line1 = line1;
        this.endpoints[index].line2 = line2;
    }

    updateEndpointCrossPosition(crossElement, x, y) {
        const size = 8;
        const line1 = crossElement.children[0];
        const line2 = crossElement.children[1];
        
        // Update first line (top-left to bottom-right)
        line1.setAttribute('x1', x - size);
        line1.setAttribute('y1', y - size);
        line1.setAttribute('x2', x + size);
        line1.setAttribute('y2', y + size);
        
        // Update second line (top-right to bottom-left)  
        line2.setAttribute('x1', x - size);
        line2.setAttribute('y1', y + size);
        line2.setAttribute('x2', x + size);
        line2.setAttribute('y2', y - size);
    }


    createEndpointCrosses() {
        this.endpoints.forEach((endpoint, index) => {
            this.createEndpointCross(endpoint.x, endpoint.y, index);
        });
        
        if (this.endpoints.length === 2) {
            this.createEndpointLine();
        }
    }

    createEndpointLine() {
       if (this.endpoints.length !== 2) return;
        
        // Remove existing line if it exists
        if (this.endpointLine) {
            this.endpointLine.remove();
        }
        
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', this.endpoints[0].x);
        line.setAttribute('y1', this.endpoints[0].y);
        line.setAttribute('x2', this.endpoints[1].x);
        line.setAttribute('y2', this.endpoints[1].y);
        line.setAttribute('stroke', '#FFFF00'); // Same color as crosses
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-dasharray', '5,5');
        
        this.svg.appendChild(line);
        this.endpointLine = line;
    }

    updateEndpointLine() {
        if (this.endpoints.length !== 2 || !this.endpointLine) return;
        
        this.endpointLine.setAttribute('x1', this.endpoints[0].x);
        this.endpointLine.setAttribute('y1', this.endpoints[0].y);
        this.endpointLine.setAttribute('x2', this.endpoints[1].x);
        this.endpointLine.setAttribute('y2', this.endpoints[1].y);
    }

    clearTN() {
        // Remove visual elements
        this.endpoints.forEach(endpoint => {
            if (endpoint.element) {
                endpoint.element.remove();
            }
        });
        
        if (this.endpointLine) {
            this.endpointLine.remove();
            this.endpointLine = null;
        }
        
        this.clearPreviewLine();
        
        // Clear data
        this.endpoints = [];
        this.updateTNStatus();
        
        // Save empty endpoints to localStorage (BLOCKING)
        this.autoSaveAnnotations();
    }
    
    handleMouseUp(e) {
        let shouldAutoSave = false;
        
        if (this.isDrawing) {
            this.isDrawing = false;
            this.finalizeRectangle();
            shouldAutoSave = true;
        }
        
        if (this.selectedRect && this.dragMode !== 'none') {
            shouldAutoSave = true;
        }
        
        this.selectedRect = null;
        this.dragMode = 'none';
        this.svg.style.cursor = 'default';
        
        // Auto-save after any operation that modifies rectangles
        if (shouldAutoSave) {
            this.autoSaveAnnotations();
        }
    }
    
    createNewRectangle(x, y) {
        const rect = {
            id: 'rect_' + Date.now(),
            x: x,
            y: y,
            width: 0,
            height: 0,
            label: this.currentStructure,
            labelString: this.currentStructure,
            color: this.getColorForLabel(this.currentStructure),
            timestamp: new Date().toISOString()
        };
        
        const svgRect = this.createSVGRectangle(rect);
        rect.element = svgRect;
        
        this.rectangles.push(rect);
        
        return rect;
    }
    
    createSVGRectangle(rect) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        // Main rectangle
        const rectEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rectEl.setAttribute('x', rect.x);
        rectEl.setAttribute('y', rect.y);
        rectEl.setAttribute('width', rect.width);
        rectEl.setAttribute('height', rect.height);
        rectEl.setAttribute('fill', 'none');
        rectEl.setAttribute('stroke', rect.color);
        rectEl.setAttribute('stroke-width', '2');
        
        // Label background
        const labelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        labelBg.setAttribute('fill', 'rgba(0,0,0,0.7)');
        labelBg.setAttribute('rx', '3');
        
        // Label text
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('fill', 'white');
        label.setAttribute('font-size', '12');
        label.setAttribute('font-family', 'Arial, sans-serif');
        label.textContent = rect.label;
        rect.labelText = label; 
        
        // Delete button - simplified X without circle background
        const deleteX = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        deleteX.setAttribute('fill', this.getInverseColor(rect.color));
        deleteX.setAttribute('font-size', '14');
        deleteX.setAttribute('font-weight', 'bold');
        deleteX.setAttribute('text-anchor', 'middle');
        deleteX.setAttribute('dominant-baseline', 'central');
        deleteX.setAttribute('stroke', rect.color);
        deleteX.setAttribute('stroke-width', '1');
        deleteX.textContent = '×';
        deleteX.style.cursor = 'pointer';
        
        // Add click handler for delete button
        deleteX.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteRectangle(rect);
        });
        
        g.appendChild(rectEl);
        g.appendChild(labelBg);
        g.appendChild(label);
        g.appendChild(deleteX);
        
        this.svg.appendChild(g);
        
        rect.rectEl = rectEl;
        rect.labelBg = labelBg;
        rect.label = label;
        rect.deleteBtn = deleteX; // Now just the X
        rect.deleteX = deleteX;
        
        return g;
    }

    // Add method to get inverse color
    getInverseColor(hexColor) {
        // Remove # if present
        const hex = hexColor.replace('#', '');
        
        // Convert to RGB
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        
        // Calculate inverse
        const invR = (255 - r).toString(16).padStart(2, '0');
        const invG = (255 - g).toString(16).padStart(2, '0');
        const invB = (255 - b).toString(16).padStart(2, '0');
        
        return `#${invR}${invG}${invB}`;
    }

    updateRectangleDisplay(rect) {
        // Update rectangle position and size
        rect.rectEl.setAttribute('x', rect.x);
        rect.rectEl.setAttribute('y', rect.y);
        rect.rectEl.setAttribute('width', rect.width);
        rect.rectEl.setAttribute('height', rect.height);
        
        // Update label position
        const labelX = rect.x;
        const labelY = rect.y - 5;
        
        rect.labelText.setAttribute('x', labelX + 5);
        rect.labelText.setAttribute('y', labelY);
        
        // Update label background
        setTimeout(() => {
            try {
                const bbox = rect.labelText.getBBox();
                rect.labelBg.setAttribute('x', labelX);
                rect.labelBg.setAttribute('y', labelY - bbox.height);
                rect.labelBg.setAttribute('width', bbox.width + 10);
                rect.labelBg.setAttribute('height', bbox.height + 4);
            } catch (e) {
                // Fallback if getBBox fails
                rect.labelBg.setAttribute('x', labelX);
                rect.labelBg.setAttribute('y', labelY - 15);
                rect.labelBg.setAttribute('width', rect.labelText.textContent.length * 8 + 10);
                rect.labelBg.setAttribute('height', 18);
            }
        }, 0);
        
        // Update delete button position (now just the X)
        rect.deleteX.setAttribute('x', rect.x + rect.width - 8);
        rect.deleteX.setAttribute('y', rect.y + 8);
    }
    
    updateRectangle(rect, x1, y1, x2, y2) {
        const x = Math.min(x1, x2);
        const y = Math.min(y1, y2);
        const width = Math.abs(x2 - x1);
        const height = Math.abs(y2 - y1);
        
        rect.x = x;
        rect.y = y;
        rect.width = width;
        rect.height = height;
        
        // Update SVG elements
        rect.rectEl.setAttribute('x', x);
        rect.rectEl.setAttribute('y', y);
        rect.rectEl.setAttribute('width', width);
        rect.rectEl.setAttribute('height', height);
        
        // Update label position
        const labelX = x;
        const labelY = y - 5;
        
        rect.labelText.setAttribute('x', labelX + 5);
        rect.labelText.setAttribute('y', labelY);
        
        // Force DOM update before getting bbox
        setTimeout(() => {
            try {
                const bbox = rect.labelText.getBBox();
                rect.labelBg.setAttribute('x', labelX);
                rect.labelBg.setAttribute('y', labelY - bbox.height);
                rect.labelBg.setAttribute('width', bbox.width + 10);
                rect.labelBg.setAttribute('height', bbox.height + 4);
            } catch (e) {
                // Fallback if getBBox fails - use labelText.textContent instead of rect.label
                rect.labelBg.setAttribute('x', labelX);
                rect.labelBg.setAttribute('y', labelY - 15);
                rect.labelBg.setAttribute('width', rect.labelText.textContent.length * 8 + 10);
                rect.labelBg.setAttribute('height', 18);
            }
        }, 0);
        
        // Update delete button position
        rect.deleteBtn.setAttribute('cx', x + width - 8);
        rect.deleteBtn.setAttribute('cy', y + 8);
        rect.deleteX.setAttribute('x', x + width - 8);
        rect.deleteX.setAttribute('y', y + 8);
    }
    
    findRectangleAt(x, y) {
        return this.rectangles.find(rect => 
            x >= rect.x && x <= rect.x + rect.width &&
            y >= rect.y && y <= rect.y + rect.height
        );
    }
    
    getDragMode(rect, x, y) {
        const edge = 10; // Edge detection threshold
        
        if (x > rect.x + rect.width - edge && y > rect.y + rect.height - edge) return 'resize-se';
        if (x < rect.x + edge && y > rect.y + rect.height - edge) return 'resize-sw';
        if (x > rect.x + rect.width - edge && y < rect.y + edge) return 'resize-ne';
        if (x < rect.x + edge && y < rect.y + edge) return 'resize-nw';
        
        return 'move';
    }
    
    handleDragResize(pos) {
        if (!this.selectedRect) return;
        
        const dx = pos.x - this.startDrag.x;
        const dy = pos.y - this.startDrag.y;
        
        if (this.dragMode === 'move') {
            this.selectedRect.x = this.startRect.x + dx;
            this.selectedRect.y = this.startRect.y + dy;
        } else if (this.dragMode === 'resize-se') {
            this.selectedRect.width = Math.max(5, this.startRect.width + dx);
            this.selectedRect.height = Math.max(5, this.startRect.height + dy);
        } else if (this.dragMode === 'resize-sw') {
            this.selectedRect.x = this.startRect.x + dx;
            this.selectedRect.width = Math.max(5, this.startRect.width - dx);
            this.selectedRect.height = Math.max(5, this.startRect.height + dy);
        } else if (this.dragMode === 'resize-ne') {
            this.selectedRect.y = this.startRect.y + dy;
            this.selectedRect.width = Math.max(5, this.startRect.width + dx);
            this.selectedRect.height = Math.max(5, this.startRect.height - dy);
        } else if (this.dragMode === 'resize-nw') {
            this.selectedRect.x = this.startRect.x + dx;
            this.selectedRect.y = this.startRect.y + dy;
            this.selectedRect.width = Math.max(5, this.startRect.width - dx);
            this.selectedRect.height = Math.max(5, this.startRect.height - dy);
        }
        
        // Update the visual display (removed autoSaveAnnotations call)
        this.updateRectangleDisplay(this.selectedRect);
    }
    
    
    updateCursor(pos) {
        const rect = this.findRectangleAt(pos.x, pos.y);
        if (rect) {
            const mode = this.getDragMode(rect, pos.x, pos.y);
            switch (mode) {
                case 'resize-se': this.svg.style.cursor = 'se-resize'; break;
                case 'resize-sw': this.svg.style.cursor = 'sw-resize'; break;
                case 'resize-ne': this.svg.style.cursor = 'ne-resize'; break;
                case 'resize-nw': this.svg.style.cursor = 'nw-resize'; break;
                case 'move': this.svg.style.cursor = 'move'; break;
            }
        } else {
            this.svg.style.cursor = 'crosshair';
        }
    }
    
    deleteRectangle(rect) {
        const index = this.rectangles.indexOf(rect);
        if (index > -1) {
            this.rectangles.splice(index, 1);
            this.usedStructures.delete(rect.labelString);
            rect.element.remove();
            this.updateDropdown();
            this.autoSaveAnnotations();
        }
    }
    
    clearAll() {
        this.rectangles.forEach(rect => rect.element.remove());
        this.rectangles = [];
        this.usedStructures.clear();
        this.autoSaveAnnotations();
        this.updateDropdown();
    }
    
    finalizeRectangle() {
        const rect = this.rectangles[this.rectangles.length - 1];
        if (rect.width < 5 || rect.height < 5) {
            this.deleteRectangle(rect);
        } else {
            this.usedStructures.add(rect.labelString);
            this.updateDropdown();
        }
    }
    
    autoSaveAnnotations() {
        const pixelMmRatio = parseFloat(this.pixelMmRatio?.value) || 0.18;
        
        const data = {
            rectangles: this.rectangles.map(rect => ({
                label: rect.labelText.textContent,
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                color: rect.color,
                timestamp: rect.timestamp
            })),
            endpoints: this.endpoints.map(endpoint => ({
                x: Math.round(endpoint.x),
                y: Math.round(endpoint.y)
            })),
            pixelMmRatio: pixelMmRatio
        };
        
        try {
            localStorage.setItem('streamlit_annotations', JSON.stringify(data));            
            console.log('Auto-saved annotations to localStorage:', data);
        } catch (error) {
            console.error('Error saving annotations:', error);
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const structures = [
        "Cisternae Magna",
        "Intracranial Translucency",
        "Nuchal Translucency",
        "Midbrain",
        "Nasal Bone",
        "Nasal Skin",
        "Nasal Tip",
        "Palate",
        "Thalami"
    ]
    
    // Get image URL from parent or use placeholder
    const imageUrl = window.imageUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5VcGxvYWQgSW1hZ2U8L3RleHQ+PC9zdmc+';
    
    // Get mask URL from window object
    const maskUrl = window.maskUrl || null;
    
    // Get initial rectangles from window object (null means use localStorage)
    const initialRectangles = window.initialRectangles && window.initialRectangles.length > 0 ? window.initialRectangles : null;
    
    // Get initial endpoints from window object (null means use localStorage)
    const initialEndpoints = window.initialEndpoints && window.initialEndpoints.length > 0 ? window.initialEndpoints : null;
    
    // Check if localStorage should be cleared
    const clearLocalStorage = window.clearLocalStorage || false;
    
    new InteractiveCanvas('interactive-canvas', imageUrl, structures, initialRectangles, maskUrl, initialEndpoints, clearLocalStorage);
});