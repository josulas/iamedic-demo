FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN find /usr/local/lib -name "__init__.py" -path "*streamlit_drawable_canvas*" -exec \
    sed -i 's/import streamlit\.elements\.image as st_image/import streamlit.elements.lib.image_utils as st_image/g' {} \;

COPY . .

RUN useradd -m -u 1000 streamlit && chown -R streamlit:streamlit /app

USER streamlit

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]