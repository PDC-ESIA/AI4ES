FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==9.0.3 pytest-cov==7.1.0 \
    pytest-json-report==1.5.0 fastapi==0.124.1 uvicorn==0.35.0
WORKDIR /opt/qa
RUN npm install --ignore-scripts --save-exact @playwright/test@1.61.1 typescript@5.9.3 \
    && npx playwright install --with-deps chromium
COPY run.py playwright.config.cjs pytest.ini validate-spec.cjs /opt/qa/
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
# Browser binaries must be readable by the unprivileged runtime user.
RUN mkdir -p /opt/browsers && cp -a /root/.cache/ms-playwright/. /opt/browsers/ \
    && chmod -R a+rX /opt/browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
USER 1000:1000
ENTRYPOINT ["python", "-I", "/opt/qa/run.py"]
