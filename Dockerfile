FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 DATA_DIR=/app/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 app
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
COPY --chown=app:app app.py science.py weather.py ./
COPY --chown=app:app catalog ./catalog
COPY --chown=app:app scripts ./scripts
RUN mkdir -p /app/data && chown app:app /app/data
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request,rasterio; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/_stcore/health',timeout=3)"
CMD ["sh", "-c", "exec streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT --server.headless=true --browser.gatherUsageStats=false"]
