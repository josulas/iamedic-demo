class InteractiveCanvas {
    constructor(containerId, imageUrl, structures, initialRectangles = []) {
        this.container = document.getElementById(containerId);
        this.structures = structures;
        this.currentStructure = structures[0];
        this.rectangles = [];
        this.isDrawing = false;
        this.selectedRect = null;
        this.dragMode = 'none';
        
        this.setupCanvas(imageUrl);
        this.setupControls();
        this.bindEvents();
        
        // Load initial rectangles if provided
        if (initialRectangles && initialRectangles.length > 0) {
            this.loadInitialRectangles(initialRectangles);
        }
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
                color: rectData.color || '#FF0000',
                timestamp: rectData.timestamp || new Date().toISOString()
            };
            
            const svgRect = this.createSVGRectangle(rect);
            rect.element = svgRect;
            
            this.rectangles.push(rect);
            
            // Force update the rectangle display to ensure labels are positioned correctly
            this.updateRectangle(rect, rect.x, rect.y, rect.x + rect.width, rect.y + rect.height);
        });
        
        this.updateAnnotationList();
        this.autoSaveAnnotations();
    }

    loadInitialRectangles(initialRectangles) {
        // Wait for image to be loaded before creating rectangles
        if (this.image.complete) {
            this.createInitialRectangles(initialRectangles);
        } else {
            this.image.onload = () => {
                this.createInitialRectangles(initialRectangles);
            };
        }
    }
    
    setupCanvas(imageUrl) {
        // Create main container
        this.container.innerHTML = `
            <div id="canvas-controls" style="margin-bottom: 10px; padding: 12px; background: #0e1117; border-radius: 8px;">
                <select id="structure-select" style="
                    margin-right: 10px; 
                    padding: 8px 12px; 
                    background: #262730; 
                    color: #fafafa; 
                    border: 1px solid #555; 
                    border-radius: 4px;
                    font-family: 'Source Sans Pro', sans-serif;
                ">
                    ${this.structures.map(s => `<option value="${s}">${s}</option>`).join('')}
                </select>
                <input type="color" id="color-picker" value="#FF0000" style="
                    margin-right: 10px; 
                    padding: 4px; 
                    background: #262730; 
                    border: 1px solid #555; 
                    border-radius: 4px;
                    cursor: pointer;
                ">
                <button id="clear-all" style="
                    padding: 8px 16px;
                    background: #ff4b4b;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-family: 'Source Sans Pro', sans-serif;
                    font-weight: 600;
                    transition: background-color 0.2s;
                " onmouseover="this.style.background='#ff6b6b'" onmouseout="this.style.background='#ff4b4b'">Clear All</button>
            </div>
            <div id="canvas-container" style="position: relative; display: inline-block; border: 2px solid #262730; border-radius: 8px; overflow: hidden;">
                <img id="main-image" src="${imageUrl}" style="display: block; max-width: 100%;">
                <svg id="annotation-svg" style="position: absolute; top: 0; left: 0; pointer-events: all;"></svg>
            </div>
            <div id="annotation-list" style="
                margin-top: 10px; 
                padding: 12px; 
                background: #0e1117; 
                border-radius: 8px;
                color: #fafafa;
                font-family: 'Source Sans Pro', sans-serif;
            "></div>
        `;
        
        this.image = document.getElementById('main-image');
        this.svg = document.getElementById('annotation-svg');
        
        // Wait for image to load then setup SVG
        this.image.onload = () => {
            this.svg.setAttribute('width', this.image.clientWidth);
            this.svg.setAttribute('height', this.image.clientHeight);
        };
    }
    
    setupControls() {
        this.structureSelect = document.getElementById('structure-select');
        this.colorPicker = document.getElementById('color-picker');
        this.clearAllBtn = document.getElementById('clear-all');
        
        this.structureSelect.addEventListener('change', (e) => {
            this.currentStructure = e.target.value;
        });
        
        this.clearAllBtn.addEventListener('click', () => {
            this.clearAll();
        });
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
    
    handleMouseDown(e) {
        const pos = this.getMousePos(e);
        const clickedRect = this.findRectangleAt(pos.x, pos.y);
        
        if (clickedRect) {
            this.selectedRect = clickedRect;
            this.dragMode = this.getDragMode(clickedRect, pos.x, pos.y);
            this.startDrag = pos;
            this.startRect = { ...clickedRect };
        } else {
            // Start drawing new rectangle
            this.isDrawing = true;
            this.startDrag = pos;
            this.createNewRectangle(pos.x, pos.y);
        }
        
        e.preventDefault();
    }
    
    handleMouseMove(e) {
        const pos = this.getMousePos(e);
        
        if (this.isDrawing && this.rectangles.length > 0) {
            // Update current rectangle being drawn
            const currentRect = this.rectangles[this.rectangles.length - 1];
            this.updateRectangle(currentRect, this.startDrag.x, this.startDrag.y, pos.x, pos.y);
        } else if (this.selectedRect && this.dragMode !== 'none') {
            // Handle dragging/resizing
            this.handleDragResize(pos);
        } else {
            // Update cursor based on hover
            this.updateCursor(pos);
        }
    }
    
    handleMouseUp(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.finalizeRectangle();
            this.autoSaveAnnotations(); // Auto-save after creating rectangle
        }
        
        if (this.selectedRect && this.dragMode !== 'none') {
            this.autoSaveAnnotations(); // Auto-save after dragging/resizing
        }
        
        this.selectedRect = null;
        this.dragMode = 'none';
        this.svg.style.cursor = 'default';
    }
    
    createNewRectangle(x, y) {
        const rect = {
            id: 'rect_' + Date.now(),
            x: x,
            y: y,
            width: 0,
            height: 0,
            label: this.currentStructure,
            color: this.colorPicker.value,
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
        
        // Delete button
        const deleteBtn = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        deleteBtn.setAttribute('r', '8');
        deleteBtn.setAttribute('fill', 'red');
        deleteBtn.setAttribute('stroke', 'white');
        deleteBtn.setAttribute('stroke-width', '1');
        deleteBtn.style.cursor = 'pointer';
        
        const deleteX = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        deleteX.setAttribute('fill', 'white');
        deleteX.setAttribute('font-size', '10');
        deleteX.setAttribute('font-weight', 'bold');
        deleteX.setAttribute('text-anchor', 'middle');
        deleteX.setAttribute('dominant-baseline', 'central');
        deleteX.textContent = '×';
        deleteX.style.cursor = 'pointer';
        deleteX.style.pointerEvents = 'none';
        
        // Add click handler for delete button
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteRectangle(rect);
        });
        
        g.appendChild(rectEl);
        g.appendChild(labelBg);
        g.appendChild(label);
        g.appendChild(deleteBtn);
        g.appendChild(deleteX);
        
        this.svg.appendChild(g);
        
        rect.rectEl = rectEl;
        rect.labelBg = labelBg;
        rect.label = label;
        rect.deleteBtn = deleteBtn;
        rect.deleteX = deleteX;
        
        return g;
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
                // Fallback if getBBox fails
                rect.labelBg.setAttribute('x', labelX);
                rect.labelBg.setAttribute('y', labelY - 15);
                rect.labelBg.setAttribute('width', rect.label.length * 8 + 10);
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
            this.selectedRect.width = this.startRect.width + dx;
            this.selectedRect.height = this.startRect.height + dy;
        }
        // Add other resize modes as needed
        this.updateRectangleDisplay(this.selectedRect);
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
        
        // Update delete button position
        rect.deleteBtn.setAttribute('cx', rect.x + rect.width - 8);
        rect.deleteBtn.setAttribute('cy', rect.y + 8);
        rect.deleteX.setAttribute('x', rect.x + rect.width - 8);
        rect.deleteX.setAttribute('y', rect.y + 8);
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
            rect.element.remove();
            this.updateAnnotationList();
            this.autoSaveAnnotations(); // Auto-save after deletion
        }
    }
    
    clearAll() {
        this.rectangles.forEach(rect => rect.element.remove());
        this.rectangles = [];
        this.updateAnnotationList();
        this.autoSaveAnnotations(); // Auto-save after clearing all
    }
    
    finalizeRectangle() {
        const rect = this.rectangles[this.rectangles.length - 1];
        if (rect.width < 5 || rect.height < 5) {
            // Remove tiny rectangles
            this.deleteRectangle(rect);
        } else {
            this.updateAnnotationList();
        }
    }
    
    updateAnnotationList() {
        const listEl = document.getElementById('annotation-list');
        listEl.innerHTML = '<h4>Annotations:</h4>' + 
            this.rectangles.map((rect, i) => 
                `<div>${i}: ${rect.labelText.textContent} at (${Math.round(rect.x)}, ${Math.round(rect.y)}) - ${Math.round(rect.width)}×${Math.round(rect.height)}</div>`
            ).join('');
    }
    
    autoSaveAnnotations() {
        const data = {
            rectangles: this.rectangles.map(rect => ({
                label: rect.labelText.textContent,
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                color: rect.color,
                timestamp: rect.timestamp
            }))
        };
        
        // Store in localStorage for Streamlit to read
        localStorage.setItem('streamlit_annotations', JSON.stringify(data));
        
        console.log('Auto-saved annotations to localStorage:', data);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const structures = [
        "Nuchal Translucency", "Nasal Bone", "Nasal Tip", "Midbrain",
        "Intracranial Translucency", "Palate", "Thalami", "Cisterna Magna", "Other"
    ];
    
    // Get image URL from parent or use placeholder
    const imageUrl = window.imageUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5VcGxvYWQgSW1hZ2U8L3RleHQ+PC9zdmc+';
    
    // Get initial rectangles from window object
    const initialRectangles = window.initialRectangles || [];
    
    new InteractiveCanvas('interactive-canvas', imageUrl, structures, initialRectangles);
});