# IAMedic Demo

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.0+-red.svg)](https://streamlit.io)

This repository contains the first iteration of the **IAMedic** product: a comprehensive web-based application for automating first trimester fetal ultrasound screening using artificial intelligence and machine learning.

## 🎯 Overview

IAMedic Demo is an AI-powered medical imaging platform designed to assist healthcare professionals in first trimester fetal ultrasound analysis. The system provides automated detection, segmentation, and measurement of key anatomical structures crucial for early pregnancy screening.

### Key Features

- **🤖 AI-Powered Analysis**: Automated detection and segmentation of fetal anatomical structures
- **📊 Real-time Processing**: Fast inference using optimized ONNX models
- **🔍 Multi-Structure Detection**: Analysis of Cisternae Magna, Intracranial Translucency, and Nuchal Translucency
- **📱 Web-based Interface**: User-friendly Streamlit frontend for healthcare professionals
- **🐳 Containerized Deployment**: Full Docker Compose setup for easy deployment
- **📈 MLflow Integration**: Model tracking and management with MLflow

## 🏗️ Architecture

The application follows a microservices architecture with the following components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│    Frontend     │◄──►│   BB-Reg Service │    │   Seg Service   │
│   (Streamlit)   │    │  (Anatomy Det.)  │    │ (Segmentation)  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                           │
└─────────────────────────────────────────────────────────────────┘
```

### Services

1. **Frontend Service** (Port 8501)
   - Streamlit-based web interface
   - Multi-language support (English/Spanish)
   - Interactive canvas for image analysis
   - Local storage for session management

2. **BB-Reg Service** (Port 8001)
   - Bounding box regression and anatomy detection
   - MLflow integration for model management
   - ONNX runtime for optimized inference
   - FastAPI-based REST API

3. **Seg Service** (Port 8002)
   - Fetal structure segmentation
   - U-Net based deep learning model
   - Image preprocessing and post-processing
   - Support for multiple anatomical classes

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/iamedic-demo.git
   cd iamedic-demo
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - Frontend: http://localhost:8501
   - BB-Reg Service API: http://localhost:8001
   - Seg Service API: http://localhost:8002

### Development Mode

For development with hot reload:

```bash
docker-compose up --build --watch
```

## 📁 Project Structure

```
iamedic-demo/
├── compose.yml                 # Docker Compose configuration
├── README.md                   # This file
├── backend/                    # Backend service (FastAPI)
│   ├── app/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── bb-reg-service/            # Bounding box regression service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── seg-service/               # Segmentation service
│   ├── main.py
│   ├── lukinoising4GP.py      # Image preprocessing utilities
│   ├── unet_fetus_segmentation.onnx
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Streamlit frontend
│   ├── app.py                 # Main application
│   ├── interactive_canvas.js  # Canvas interaction scripts
│   ├── lang_pack_*.json       # Language packs
│   ├── config.toml            # Streamlit configuration
│   ├── Dockerfile
│   └── requirements.txt
└── models-training/           # ML model training and research
    ├── *.ipynb                # Jupyter notebooks
    ├── dataset/               # Training datasets
    ├── onnx_exports/          # Exported ONNX models
    └── preprocessed_images/   # Processed training data
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
# API Endpoints
BB_REG_SERVICE_URL=http://bb-reg-service:8000
SEG_SERVICE_URL=http://seg-service:8000

# MLflow Configuration
MLFLOW_URI=http://host.docker.internal:8080
```

### Service Ports

- Frontend: `8501`
- BB-Reg Service: `8001`
- Seg Service: `8002`

## 🧠 Machine Learning Models

The application uses several specialized models:

### 1. Anatomy Detector (BB-Reg Service)
- **Purpose**: Detect and classify fetal anatomical structures
- **Technology**: ONNX optimized model
- **Integration**: MLflow model registry
- **Classes**: Multiple anatomical landmarks

### 2. Fetal Segmentation (Seg Service)
- **Purpose**: Precise segmentation of fetal structures
- **Architecture**: U-Net based neural network
- **Classes**:
  - Cisternae Magna
  - Intracranial Translucency
  - Nuchal Translucency

### 3. Image Preprocessing
- **Lukinoising**: Custom noise reduction algorithm
- **Normalization**: Standardized image preprocessing
- **Resizing**: Adaptive image scaling (400x600 target)

## 🔬 Development

### Local Development Setup

1. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies for each service:**
   ```bash
   pip install -r frontend/requirements.txt
   pip install -r seg-service/requirements.txt
   pip install -r bb-reg-service/requirements.txt
   ```

3. **Run services individually:**
   ```bash
   # Frontend
   cd frontend && streamlit run app.py

   # Seg Service
   cd seg-service && uvicorn main:app --reload --port 8002

   # BB-Reg Service
   cd bb-reg-service && uvicorn main:app --reload --port 8001
   ```

### API Documentation

- **Seg Service API**: http://localhost:8002/docs
- **BB-Reg Service API**: http://localhost:8001/docs

### Testing

```bash
# Run tests for backend services
cd backend && python -m pytest tests/

# Health checks
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## 📊 Model Training

The `models-training/` directory contains Jupyter notebooks for:

- **EDA.ipynb**: Exploratory Data Analysis
- **localizer.ipynb**: Anatomy localization model training
- **segmenter.ipynb**: Segmentation model training
- **localizer-inference.ipynb**: Inference testing
- **segmenter-inference.ipynb**: Segmentation testing

### Training Data

- Dataset format: ObjectDetection.xlsx
- Preprocessed images: `preprocessed_images/`
- Segmentation masks: `segmentations/`

## 🌐 Internationalization

The frontend supports multiple languages:

- **English**: `lang_pack_en.json`
- **Spanish**: `lang_pack_es.json`

## 🐳 Docker Deployment

### Production Deployment

```bash
# Build and start all services
docker-compose up -d --build

# Scale services if needed
docker-compose up -d --scale seg-service=2

# Check service health
docker-compose ps
```

### Health Monitoring

All services include health checks:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 60 seconds

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Include docstrings for functions and classes
- Write tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue in the GitHub repository
- Contact the development team
- Check the documentation in individual service README files

## 🙏 Acknowledgments

- FastAPI framework for robust API development
- Streamlit for rapid frontend development
- ONNX Runtime for optimized model inference
- MLflow for experiment tracking and model management
- The open-source community for the various libraries used

---

**Note**: This is a demo version intended for research and development purposes. For production medical use, ensure compliance with relevant medical device regulations and standards.
